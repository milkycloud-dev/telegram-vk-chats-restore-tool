"""Parse the Telegram Desktop HTML export into a list of Event objects.

Media binaries are mostly absent from this export; when a referenced file is
present on disk it is sent for real, otherwise a labeled placeholder is emitted.
"""
import datetime as dt
import glob
import os
import re
from html import unescape

import config
import models
from models import Attachment, Event

_MSG_SPLIT = re.compile(r'(?=<div class="message )')
_CLASS_RE = re.compile(r'<div class="message ([^"]*)"')
_FROM_RE = re.compile(r'<div class="from_name">\s*(.*?)\s*</div>', re.S)
_TEXT_RE = re.compile(r'<div class="text">\s*(.*?)\s*</div>', re.S)
_DATE_TITLE_RE = re.compile(r'<div class="pull_right date details" title="([^"]+)"')
_SERVICE_BODY_RE = re.compile(r'<div class="body details">\s*(.*?)\s*</div>', re.S)
_REPLY_RE = re.compile(r'<div class="reply_to details">', re.S)
_FWD_RE = re.compile(r'<div class="forwarded body">', re.S)
_ANCHOR_RE = re.compile(r'<a class="([^"]*)" href="([^"]*)"[^>]*>(.*?)</a>', re.S)
_STATUS_RE = re.compile(r'<div class="status details">\s*(.*?)\s*</div>', re.S)
_TITLE_RE = re.compile(r'<div class="title bold">\s*(.*?)\s*</div>', re.S)
_CALL_RE = re.compile(r'media_call', re.S)
_CALL_SUCCESS_RE = re.compile(r'media_call\s+success', re.S)
_DATE_FULL_RE = re.compile(
    r'pull_right date details" title="(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2})')
_DUR_RE = re.compile(r'\((\d+)\s*seconds?\)')
_EMOJI_RE = re.compile(r'<img[^>]*class="emoji"[^>]*alt="([^"]*)"[^>]*>', re.S)
_TAG_RE = re.compile(r'<[^>]+>')


def _fmt_call_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} ч")
    if m:
        parts.append(f"{m} мин")
    if s or not parts:
        parts.append(f"{s} сек")
    return " ".join(parts)


def _format_call(block: str) -> str:
    """Build a detailed call line: direction, date, from–to time and duration.

    NOTE: the Telegram HTML export does NOT record whether a call was audio or
    video (both are exported as `media_call`), so the type cannot be shown."""
    status_m = _STATUS_RE.search(block)
    status = _html_to_text(status_m.group(1)) if status_m else ""
    low = status.lower()

    direction = "исходящий" if "outgoing" in low else (
        "входящий" if "incoming" in low else "")
    dm = _DUR_RE.search(status)
    dur = int(dm.group(1)) if dm else 0

    if "missed" in low:
        head = "📞 Пропущенный звонок"
    elif "cancelled" in low:
        head = "📞 Отменённый звонок"
    elif "declined" in low:
        head = "📞 Отклонённый звонок"
    elif _CALL_SUCCESS_RE.search(block) or dur > 0:
        head = "📞 Звонок"
    else:
        head = "📞 Звонок (не отвечен)"
    if direction:
        head += f" · {direction}"

    lines = [head]
    tm = _DATE_FULL_RE.search(block)
    if tm:
        d, mo, y, hh, mm, ss = (int(x) for x in tm.groups())
        start = dt.datetime(y, mo, d, hh, mm, ss)
        date_str = f"{d:02d}.{mo:02d}.{y}"
        if dur > 0:
            end = start + dt.timedelta(seconds=dur)
            lines.append(f"📅 {date_str}, {start:%H:%M:%S} – {end:%H:%M:%S}")
        else:
            lines.append(f"📅 {date_str}, {start:%H:%M:%S}")
    if dur > 0:
        lines.append(f"⏱ Длительность: {_fmt_call_duration(dur)}")
    return "\n".join(lines)


def _html_to_text(html: str) -> str:
    html = _EMOJI_RE.sub(lambda m: m.group(1), html)
    html = re.sub(r'<br\s*/?>', '\n', html)

    def _a(m):
        href, inner = m.group(1), _TAG_RE.sub('', m.group(2))
        inner = unescape(inner).strip()
        href = unescape(href).strip()
        if href.startswith('http') and href != inner:
            return f"{inner} ({href})" if inner else href
        return inner
    html = re.sub(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', _a, html, flags=re.S)
    html = _TAG_RE.sub('', html)
    return unescape(html).strip()


def _clean_name(raw: str) -> str:
    # Forwarded channel names carry a trailing <span class="date ...">; strip it.
    raw = re.split(r'<span', raw)[0]
    return unescape(_TAG_RE.sub('', raw)).strip()


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower().lstrip('.')


def _media_from_anchor(classes: str, href: str, inner: str, tg_dir: str) -> Attachment:
    href = unescape(href)
    folder = href.split('/')[0] if '/' in href else ''
    name = href.split('/')[-1]
    local = os.path.join(tg_dir, href.replace('/', os.sep))
    exists = os.path.exists(local)
    status = _STATUS_RE.search(inner)
    dur = status.group(1).strip() if status else ""

    if folder == 'photos':
        if exists:
            return Attachment(models.PHOTO, local_path=local, note="[фото]")
        return Attachment(models.TEXT_NOTE, note="[фото]")

    if folder == 'stickers':
        if exists:
            return Attachment(models.STICKER, local_path=local, note="[стикер]")
        return Attachment(models.TEXT_NOTE, note="[стикер]")

    if folder == 'voice_messages':
        note = f"[голосовое сообщение{(' ' + dur) if dur else ''}]"
        if exists:
            return Attachment(models.VOICE, local_path=local, note=note)
        return Attachment(models.TEXT_NOTE, note=note)

    if folder == 'round_video_messages':
        if exists:
            return Attachment(models.VIDEO_NOTE, local_path=local, note="[видеосообщение]")
        return Attachment(models.TEXT_NOTE, note="[видеосообщение]")

    if folder == 'video_files':
        e = _ext(name)
        # Telegram video stickers are .webm files named "sticker (N).webm".
        if e == 'webm' and (name.lower().startswith('sticker') or 'media_photo' in classes):
            if exists:
                return Attachment(models.STICKER, local_path=local, file_name=name,
                                  note="[стикер]")
            return Attachment(models.TEXT_NOTE, note="[стикер]")
        kind = models.ANIMATION if e in ('gif', 'webm') else models.VIDEO
        if exists:
            return Attachment(kind, local_path=local, file_name=name, note="[видео]")
        return Attachment(models.TEXT_NOTE, note="[видео]")

    # files/ and anything else -> document
    title = _TITLE_RE.search(inner)
    fname = (title.group(1).strip() if title else name)
    note = f"[файл: {fname}]"
    if exists:
        e = _ext(name)
        if e in ('jpg', 'jpeg', 'png', 'webp'):
            return Attachment(models.PHOTO, local_path=local, note=note)
        if e == 'gif':
            return Attachment(models.ANIMATION, local_path=local, note=note)
        if e in ('mp4',):
            return Attachment(models.VIDEO, local_path=local, note=note)
        if e in ('ogg', 'oga', 'mp3', 'm4a', 'wav'):
            return Attachment(models.AUDIO, local_path=local, note=note)
        return Attachment(models.DOCUMENT, local_path=local, file_name=fname, note=note)
    return Attachment(models.TEXT_NOTE, note=note)


def _file_index(path: str) -> int:
    base = os.path.basename(path)
    m = re.search(r'messages(\d*)\.html', base)
    if not m:
        return 0
    return int(m.group(1)) if m.group(1) else 1


def parse(tg_dir: str | None = None) -> list[Event]:
    tg_dir = tg_dir or config.TG_DIR
    files = sorted(glob.glob(os.path.join(tg_dir, 'messages*.html')),
                   key=_file_index)
    events: list[Event] = []
    current_sender = config.TG_DEFAULT_SENDER
    current_day = ""

    for fp in files:
        html = open(fp, encoding='utf-8').read()
        body_start = html.find('<div class="history">')
        if body_start != -1:
            html = html[body_start:]
        for block in _MSG_SPLIT.split(html):
            cm = _CLASS_RE.search(block)
            if not cm:
                continue
            classes = cm.group(1)

            if 'service' in classes:
                sb = _SERVICE_BODY_RE.search(block)
                if sb:
                    current_day = _html_to_text(sb.group(1))
                continue

            joined = 'joined' in classes
            if not joined:
                fm = _FROM_RE.search(block)
                if fm:
                    name = _clean_name(fm.group(1)).lower()
                    current_sender = config.TG_SENDER_MAP.get(name, config.TG_DEFAULT_SENDER)
            sender = current_sender
            display_name = config.DISPLAY_NAMES.get(sender, sender)

            text_parts = []

            if _REPLY_RE.search(block):
                text_parts.append("↪ в ответ")

            if _FWD_RE.search(block):
                # The forwarded source name is the from_name that carries a date span.
                fwd_names = re.findall(r'<div class="from_name">\s*(.*?)\s*</div>', block, re.S)
                src = ""
                for n in fwd_names:
                    if '<span' in n:
                        src = _clean_name(n)
                        break
                text_parts.append(f"[переслано{(' от ' + src) if src else ''}]")

            for tm in _TEXT_RE.finditer(block):
                t = _html_to_text(tm.group(1))
                if t:
                    text_parts.append(t)

            attachments = []
            for am in _ANCHOR_RE.finditer(block):
                cls, href, inner = am.group(1), am.group(2), am.group(3)
                if 'media' not in cls and 'photo_wrap' not in cls and \
                   'sticker_wrap' not in cls and 'wrap' not in cls:
                    continue
                attachments.append(_media_from_anchor(cls, href, inner, tg_dir))

            if _CALL_RE.search(block) and not attachments:
                text_parts.append(_format_call(block))

            text = "\n".join(p for p in text_parts if p).strip()
            if not text and not attachments:
                continue

            events.append(Event(source="tg", sender=sender, date=0,
                                text=text, attachments=attachments,
                                day_label=current_day,
                                sender_display_name=display_name))
    return events


def extract_sender_names(tg_dir: str) -> list[str]:
    """Extract unique sender names from a Telegram HTML export folder.

    Returns a sorted list of display names found in from_name divs.
    """
    if not tg_dir or not os.path.isdir(tg_dir):
        return []
    try:
        names = set()
        files = sorted(glob.glob(os.path.join(tg_dir, 'messages*.html')),
                       key=_file_index)
        for fp in files:
            html = open(fp, encoding='utf-8').read()
            body_start = html.find('<div class="history">')
            if body_start != -1:
                html = html[body_start:]
            for block in _MSG_SPLIT.split(html):
                cm = _CLASS_RE.search(block)
                if not cm:
                    continue
                classes = cm.group(1)
                if 'service' in classes:
                    continue
                if 'joined' in classes:
                    continue
                fm = _FROM_RE.search(block)
                if fm:
                    name = _clean_name(fm.group(1))
                    if name:
                        names.add(name)
        return sorted(names)
    except Exception:
        return []
