"""Runtime configuration for the VK + Telegram → Telegram replay tool.

User-editable values live in `settings.json` (see `settings_manager.py`).
This module holds defaults and is patched per-task via `apply_task()`.
"""
import os

# --- Loaded from settings.json (defaults below) --------------------------------
MODE = "vk_and_tg"          # vk_only | tg_only | vk_and_tg

BOT_TOKENS: dict[str, str] = {}
SYSTEM_BOT = ""              # bot key used for date/section headers

CHAT_ID = 0

VK_SENDER_MAP: dict = {}
VK_DEFAULT_SENDER = ""

TG_SENDER_MAP: dict = {}
TG_DEFAULT_SENDER = ""

MULTICHAT = False             # single-bot mode with [Sender] prefix
MULTICHAT_BOT = ""            # which bot key to use in multichat mode
DISPLAY_NAMES: dict[str, str] = {}  # bot_key -> display name for multichat prefix

ATTACHMENTS_FILTER: dict[str, bool] = {}  # attachment_kind -> bool (True = send)

MIN_INTERVAL_SECONDS = 1.5
JITTER_SECONDS = 0.4
ERROR_BACKOFF_SECONDS = 5.0
HTTP_TIMEOUT = (15, 120)

MEDIA_DOWNLOAD_ATTEMPTS = 12
MEDIA_RETRY_BACKOFF_SECONDS = 5.0
SEND_MEDIA_ATTEMPTS = 6

SEND_DATE_HEADERS = True
SEND_SECTION_HEADERS = True
PLACEHOLDERS_FOR_MISSING = True

# --- Paths (internal + from settings) ----------------------------------------
EXPORTER_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(EXPORTER_DIR)

VK_EXPORTS: list[dict] = []   # [{"path": "...", "label": "..."}]
VK_JSON = ""                   # first VK export path (compat)
VK_MEDIA_MIRRORS: list[tuple[str, str]] = []

TG_DIRS: list[str] = []
TG_SECTION_LABELS: list[str] = []
TG_DIR = ""
TG_FILES_DIR = ""

CACHE_DIR = os.path.join(EXPORTER_DIR, "cache")
STATE_FILE = os.path.join(EXPORTER_DIR, "state.json")
LOG_FILE = os.path.join(EXPORTER_DIR, "replay.log")
RESULTS_FILE = os.path.join(EXPORTER_DIR, "results.jsonl")
NOT_SENT_FILE = os.path.join(EXPORTER_DIR, "not_sent.log")

HTTP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Auto-load settings.json when the package is imported (CLI / verify / GUI).
try:
    from settings_manager import load_and_apply
    load_and_apply()
except Exception:
    pass
