"""Parse the VkOpt JSON export into a chronological list of Event objects."""
import json
import os

import config
import media_map
import models
from models import Attachment, Event

_IMG_EXT = {"jpg", "jpeg", "png", "webp", "bmp", "heic"}
_PHOTO_KEYS = ["photo_2560", "photo_1280", "photo_807", "photo_604",
               "photo_512", "photo_256", "photo_130", "photo_75"]


def _photo_candidates(photo: dict) -> list[str]:
    """Photo URLs from largest to smallest."""
    cands: list[str] = []
    sizes = photo.get("sizes")
    if isinstance(sizes, list) and sizes:
        for s in sorted(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0),
                        reverse=True):
            u = s.get("url") or s.get("src")
            if u:
                cands.append(u)
    for k in _PHOTO_KEYS:
        if photo.get(k):
            cands.append(photo[k])
    return cands


def _photo_local_or_url(photo: dict) -> tuple[str | None, str]:
    """Prefer the largest locally-downloaded size; fall back to the largest URL."""
    cands = _photo_candidates(photo)
    for u in cands:
        lp = media_map.lookup(u)
        if lp:
            return lp, u
    return None, (cands[0] if cands else "")


def _sticker_url(st: dict) -> str:
    """Execute the sticker url operation."""
    for k in ("photo_512", "photo_352", "photo_256", "photo_128", "photo_64"):
        if st.get(k):
            return st[k]
    return ""


def _parse_attachment(att: dict) -> tuple[list[Attachment], str]:
    """Return (attachments, extra_text)."""
    t = att.get("type")
    obj = att.get(t, {}) if isinstance(att.get(t), dict) else {}

    if t == "photo":
        local, url = _photo_local_or_url(obj)
        if local or url:
            return [Attachment(models.PHOTO, local_path=local, url=url,
                               note="[фото недоступно]")], ""
        return [], "[фото]"

    if t == "sticker":
        url = _sticker_url(obj.get("sticker", obj))
        return [Attachment(models.STICKER, url=url,
                           needs_sticker_conversion=True, note="[стикер]")], ""

    if t == "graffiti":
        cands = _photo_candidates(obj)
        url = obj.get("url") or (cands[0] if cands else "")
        local = media_map.lookup(url) if url else None
        return [Attachment(models.PHOTO, local_path=local, url=url,
                           note="[граффити]")], ""

    if t == "doc":
        ext = (obj.get("ext") or "").lower()
        title = obj.get("title") or "file"
        preview = obj.get("preview") or {}
        if "audio_msg" in preview:
            am = preview["audio_msg"]
            local = media_map.lookup(am.get("link_ogg")) or media_map.lookup(am.get("link_mp3"))
            url = am.get("link_ogg") or am.get("link_mp3") or obj.get("url")
            dur = int(am.get("duration") or 0)
            return [Attachment(models.VOICE, local_path=local, url=url, duration=dur,
                               note=f"[голосовое сообщение, {dur}с]")], ""
        doc_local = media_map.lookup(obj.get("url"))
        if ext == "gif":
            return [Attachment(models.ANIMATION, local_path=doc_local,
                               url=obj.get("url"), file_name=title, note="[GIF]")], ""
        if ext in _IMG_EXT:
            return [Attachment(models.PHOTO, local_path=doc_local,
                               url=obj.get("url"), note="[изображение]")], ""
        return [Attachment(models.DOCUMENT, local_path=doc_local, url=obj.get("url"),
                           file_name=title, note=f"[файл: {title}]")], ""

    if t == "audio":
        artist = obj.get("artist", "")
        title = obj.get("title", "")
        dur = int(obj.get("duration") or 0)
        label = " — ".join(p for p in (artist, title) if p) or "audio"
        local = media_map.lookup(obj.get("url"))
        return [Attachment(models.AUDIO, local_path=local, url=obj.get("url"),
                           title=title, performer=artist, duration=dur,
                           note=f"🎵 {label}")], ""

    if t == "video":
        # Videos (YouTube and other external/VK videos) are NOT downloaded — the
        # thumbnail URLs often SSL-error. We just post a link to the chat.
        title = obj.get("title", "видео")
        platform = obj.get("platform", "")
        owner, vid = obj.get("owner_id"), obj.get("id")
        link = f"https://vk.com/video{owner}_{vid}" if owner and vid else ""
        cap = f"🎬 {title}" + (f" ({platform})" if platform else "")
        if link:
            cap += f"\n{link}"
        return [], cap

    if t == "link":
        link = obj.get("url", "")
        title = obj.get("title", "") or link
        return [], f"🔗 {title}: {link}" if link else ""

    if t == "wall":
        txt = obj.get("text", "")
        return [], "[репост со стены]" + (f"\n{txt}" if txt else "")

    if t == "wall_reply":
        return [], "[комментарий со стены]"

    if t == "market" or t == "market_album":
        return [], f"[товар: {obj.get('title', '')}]"

    if t == "poll":
        return [], f"[опрос: {obj.get('question', '')}]"

    if t == "gift":
        # Gifts are sent as stickers (webp) with a separate gift label.
        url = obj.get("thumb_256") or obj.get("thumb_96") or obj.get("thumb_48")
        if url:
            local = media_map.lookup(url)
            return [Attachment(models.GIFT, local_path=local, url=url,
                               needs_sticker_conversion=True, is_gift=True,
                               note="🎁 [подарок]")], ""
        return [], "🎁 [подарок]"

    if t == "call":
        return [], "[звонок]"

    if t == "story":
        return [], "[история]"

    if t == "geo":
        return [], "[геолокация]"

    return [], f"[вложение: {t}]"


def _collect(msg: dict) -> tuple[list[Attachment], list[str]]:
    """Execute the collect operation."""
    atts: list[Attachment] = []
    notes: list[str] = []
    for att in msg.get("attachments", []) or []:
        a, txt = _parse_attachment(att)
        atts.extend(a)
        if txt:
            notes.append(txt)
    return atts, notes


def parse(vk_json_path: str | None = None) -> list[Event]:
    """Parse VK JSON export into Event list.

    Args:
        vk_json_path: explicit path to JSON file; falls back to config.VK_JSON.
    """
    path = vk_json_path or config.VK_JSON
    if not path or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.sort(key=lambda m: m.get("date", 0))

    events: list[Event] = []
    for msg in data:
        from_id = str(msg.get("from_id", ""))
        sender = config.VK_SENDER_MAP.get(from_id, config.VK_DEFAULT_SENDER)
        # Resolve display name for multichat
        display_name = config.DISPLAY_NAMES.get(sender, sender)
        text_parts = []

        body = (msg.get("body") or "").strip()

        # Reply quote.
        reply = msg.get("reply_message")
        if isinstance(reply, dict):
            rb = (reply.get("body") or "").strip()
            quote = rb if rb else "вложение"
            if len(quote) > 120:
                quote = quote[:117] + "…"
            text_parts.append(f"↪ в ответ на: «{quote}»")

        if body:
            text_parts.append(body)

        atts, notes = _collect(msg)
        text_parts.extend(notes)

        # Forwarded messages (flatten text + media).
        for fwd in msg.get("fwd_messages", []) or []:
            fb = (fwd.get("body") or "").strip()
            fa, fnotes = _collect(fwd)
            head = "[переслано]"
            if fb:
                head += f" {fb}"
            text_parts.append(head)
            text_parts.extend(fnotes)
            atts.extend(fa)

        text = "\n".join(p for p in text_parts if p).strip()
        events.append(Event(source="vk", sender=sender,
                            date=int(msg.get("date", 0)),
                            text=text, attachments=atts,
                            sender_display_name=display_name))
    return events


def extract_sender_ids(vk_json_path: str) -> list[str]:
    """Extract unique sender (from_id) values from a VK JSON export.

    Returns a list of string IDs, sorted, for display in the GUI.
    """
    if not vk_json_path or not os.path.isfile(vk_json_path):
        return []
    try:
        with open(vk_json_path, encoding="utf-8") as f:
            data = json.load(f)
        ids = set()
        for msg in data:
            fid = msg.get("from_id")
            if fid is not None:
                ids.add(str(fid))
        return sorted(ids)
    except Exception:
        return []
