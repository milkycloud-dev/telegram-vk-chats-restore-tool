"""Normalized data model shared by the VK and Telegram parsers."""
from dataclasses import dataclass, field
from typing import Optional


# Attachment kinds the sender knows how to handle.
PHOTO = "photo"
STICKER = "sticker"            # static sticker -> sendSticker (webp)
ANIMATION = "animation"        # gif / animated -> sendAnimation
VOICE = "voice"               # voice message -> sendVoice (ogg)
AUDIO = "audio"               # music track -> sendAudio (mp3)
VIDEO = "video"               # video file -> sendVideo
VIDEO_NOTE = "video_note"     # round video -> sendVideoNote
DOCUMENT = "document"         # any file -> sendDocument
TEXT_NOTE = "text_note"       # render as plain text (calls, links, walls, etc.)
GIFT = "gift"                 # VK gift -> sendSticker + label


@dataclass
class Attachment:
    kind: str
    # Source of the binary, in priority order: a local file, a URL we download,
    # or nothing (then `note` is used as a placeholder).
    local_path: Optional[str] = None
    url: Optional[str] = None
    # Convert downloaded bytes to a sticker-ready webp before sending.
    needs_sticker_conversion: bool = False
    # Optional caption / metadata.
    caption: str = ""
    title: str = ""
    performer: str = ""
    duration: int = 0
    width: int = 0
    height: int = 0
    file_name: str = ""
    # Text used if the media cannot be obtained (placeholder).
    note: str = ""
    # True for VK gift attachments (sent as sticker + gift label).
    is_gift: bool = False


@dataclass
class Event:
    source: str               # "vk" | "tg"
    sender: str               # bot key (arbitrary, e.g. "bot1", "bot2")
    date: int                 # unix timestamp (0 if unknown)
    text: str = ""
    attachments: list = field(default_factory=list)  # list[Attachment]
    # Human-readable date string for day headers (from the export when available).
    day_label: str = ""
    # Which source chat this event came from (e.g. "Телеграм 2"); for the GUI.
    chat_label: str = ""
    # Display name of the sender for multichat mode prefix.
    sender_display_name: str = ""
