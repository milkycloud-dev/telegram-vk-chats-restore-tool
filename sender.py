"""Turn normalized Events/Attachments into actual Telegram bot sends, with
graceful fallback to text placeholders when media is missing or expired.

Supports:
  - Regular mode: each event goes through its assigned bot.
  - Multichat mode: all events go through one bot with a [SenderName] prefix.
  - Attachment filter: skip disabled attachment kinds.
  - Gift handling: send as sticker + separate gift label message.
"""
import os

import config
import media
import models
from control import CONTROL, SkipRequested
from telegram_client import get_bot, TelegramError

# Attachment kinds that support a caption on their send method.
_CAPTIONABLE = {models.PHOTO, models.VIDEO, models.AUDIO, models.VOICE,
                models.ANIMATION, models.DOCUMENT}

_STAT_KEY = {
    models.PHOTO: "photo", models.STICKER: "sticker", models.VOICE: "voice",
    models.AUDIO: "audio", models.VIDEO: "video", models.VIDEO_NOTE: "video_note",
    models.ANIMATION: "animation", models.DOCUMENT: "document",
    models.GIFT: "sticker",  # gifts count as stickers in stats
}


def _resolve(att, ext: str) -> str | None:
    if att.local_path and os.path.exists(att.local_path):
        return att.local_path
    if att.url:
        return media.download(att.url, ext)
    return None


def _is_filtered(att) -> bool:
    """Check if this attachment kind is disabled by the filter."""
    filt = config.ATTACHMENTS_FILTER
    if not filt:
        return False  # no filter = send everything
    kind = models.GIFT if att.is_gift else att.kind
    return not filt.get(kind, True)


def _send_media(bot, att, caption: str) -> bool:
    """Try to send one media attachment. Returns True on success."""
    try:
        # Gift: send as sticker (webp) + separate gift label
        if att.is_gift or att.kind == models.GIFT:
            if att.local_path and os.path.exists(att.local_path):
                p = att.local_path
            elif att.url:
                p = media.to_sticker_webp(att.url)
            else:
                p = None
            if not p:
                return False
            # Convert to webp if needed
            if att.needs_sticker_conversion and att.url:
                webp = media.to_sticker_webp(att.url)
                if webp:
                    p = webp
            try:
                bot.send_sticker(p)
            except TelegramError:
                # Fallback: send as photo
                bot.send_photo(p, "")
            # Always send the gift label as a separate message
            bot.send_message("🎁 [подарок]")
            return True

        if att.kind == models.PHOTO:
            p = _resolve(att, "jpg")
            if not p:
                return False
            bot.send_photo(p, caption)
            return True

        if att.kind == models.STICKER:
            if att.local_path and os.path.exists(att.local_path):
                p = att.local_path
            elif att.url:
                p = media.to_sticker_webp(att.url)
            else:
                p = None
            if not p:
                return False
            try:
                bot.send_sticker(p)
                return True
            except TelegramError:
                ext = os.path.splitext(p)[1].lower()
                try:
                    if ext in (".webm", ".gif", ".mp4"):
                        bot.send_animation(p, caption)
                    elif ext in (".webp", ".png", ".jpg", ".jpeg"):
                        bot.send_photo(p, caption)
                    else:
                        bot.send_document(p, caption)
                    return True
                except TelegramError:
                    return False

        if att.kind == models.VOICE:
            p = _resolve(att, "ogg")
            if not p:
                return False
            # VK voice files are mp3; convert to ogg/opus for a real voice bubble.
            if p.lower().endswith(".mp3"):
                ogg = media.mp3_to_opus(p)
                if ogg:
                    bot.send_voice(ogg, caption, att.duration)
                    return True
                bot.send_audio(p, caption, duration=att.duration)  # fallback
                return True
            bot.send_voice(p, caption, att.duration)
            return True

        if att.kind == models.AUDIO:
            p = _resolve(att, "mp3")
            if not p:
                return False
            bot.send_audio(p, caption, att.title, att.performer, att.duration)
            return True

        if att.kind == models.VIDEO:
            p = _resolve(att, "mp4")
            if not p:
                return False
            bot.send_video(p, caption, att.duration)
            return True

        if att.kind == models.VIDEO_NOTE:
            p = _resolve(att, "mp4")
            if not p:
                return False
            bot.send_video_note(p)
            return True

        if att.kind == models.ANIMATION:
            ext = "gif" if (att.file_name.lower().endswith("gif")) else "mp4"
            p = _resolve(att, ext)
            if not p:
                return False
            bot.send_animation(p, caption)
            return True

        if att.kind == models.DOCUMENT:
            ext = os.path.splitext(att.file_name)[1].lstrip(".") or "bin"
            p = _resolve(att, ext)
            if not p:
                return False
            bot.send_document(p, caption)
            return True

    except TelegramError:
        return False
    return False


def _multichat_prefix(event) -> str:
    """Build the [SenderName] prefix for multichat mode."""
    name = event.sender_display_name or event.sender
    return f"[{name}]"


def send_event(event) -> dict:
    """Send one event. Returns a result dict describing exactly what was sent,
    placeheld, skipped or errored (used for the ledger)."""
    # In multichat mode, all messages go through the multichat bot.
    if config.MULTICHAT and config.MULTICHAT_BOT:
        bot = get_bot(config.MULTICHAT_BOT)
    else:
        bot = get_bot(event.sender)

    result = {"text": False, "sent": [], "placeholder": [], "skipped": [], "error": []}
    CONTROL.stats.set(current_sender=event.sender, current_kind="text", current_file="")

    media_atts = [a for a in event.attachments
                  if a.kind != models.TEXT_NOTE and not _is_filtered(a)]
    filtered_atts = [a for a in event.attachments
                     if a.kind != models.TEXT_NOTE and _is_filtered(a)]
    note_atts = [a for a in event.attachments if a.kind == models.TEXT_NOTE]

    # Count filtered attachments as skipped
    for a in filtered_atts:
        result["skipped"].append(a.kind)
        CONTROL.stats.inc("skipped")

    text = event.text or ""
    extra_notes = [a.note for a in note_atts if a.note]
    if extra_notes:
        text = (text + "\n" + "\n".join(extra_notes)).strip()

    # In multichat mode, prepend [SenderName] to text
    if config.MULTICHAT:
        prefix = _multichat_prefix(event)
        if text:
            text = f"{prefix}\n{text}"
        elif not media_atts:
            # No text and no media — nothing to send
            return result

    if not media_atts:
        if text:
            bot.send_message(text[:4096])
            CONTROL.stats.inc("text")
            result["text"] = True
        return result

    first = media_atts[0]
    caption = ""
    text_sent = False
    if text:
        if len(text) <= 1024 and first.kind in _CAPTIONABLE and not first.is_gift:
            caption = text
        else:
            bot.send_message(text[:4096])
            CONTROL.stats.inc("text")
            text_sent = True
            result["text"] = True

    for i, att in enumerate(media_atts):
        cap = caption if (i == 0 and caption) else ""
        loc = att.local_path or att.url or ""
        CONTROL.stats.set(current_file=os.path.basename(loc) if loc else "",
                          current_kind=att.kind, current_sender=event.sender)

        # In multichat mode with media but no text yet sent, send the prefix
        if config.MULTICHAT and i == 0 and not text_sent and not caption:
            prefix = _multichat_prefix(event)
            bot.send_message(prefix)
            CONTROL.stats.inc("text")
            text_sent = True

        try:
            ok = _send_media(bot, att, cap)
        except SkipRequested:
            CONTROL.clear_skip()
            CONTROL.stats.inc("skipped")
            CONTROL.stats.set(last_error=f"skipped {att.kind}")
            result["skipped"].append(att.kind)
            if i == 0 and caption and not text_sent:
                try:
                    bot.send_message(caption[:4096])
                    CONTROL.stats.inc("text")
                    text_sent = True
                    result["text"] = True
                except SkipRequested:
                    CONTROL.clear_skip()
            continue
        if ok:
            CONTROL.stats.inc(_STAT_KEY.get(att.kind, "document"))
            result["sent"].append(att.kind)
        elif config.PLACEHOLDERS_FOR_MISSING:
            note = att.note or f"[{att.kind}]"
            if i == 0 and caption and not text_sent:
                note = caption + "\n" + note
                text_sent = True
            try:
                bot.send_message(note[:4096])
                CONTROL.stats.inc("placeholders")
                result["placeholder"].append(att.kind)
            except SkipRequested:
                CONTROL.clear_skip()
                CONTROL.stats.inc("skipped")
                result["skipped"].append(att.kind)
        else:
            result["error"].append(att.kind)
    return result
