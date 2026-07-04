"""Load / save / validate user settings and apply them to the runtime `config`
module.  Settings live in `settings.json` next to this file (full Windows paths
supported).

Settings are stored as a list of *tasks*, each describing one chat-replay job.
"""
from __future__ import annotations

import copy
import json
import os

import config
from i18n import t

EXPORTER_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(EXPORTER_DIR, "settings.json")

# Modes understood by build_actions().
MODE_VK_ONLY = "vk_only"
MODE_TG_ONLY = "tg_only"
MODE_VK_AND_TG = "vk_and_tg"
MODES = (MODE_VK_ONLY, MODE_TG_ONLY, MODE_VK_AND_TG)
MODE_LABELS = {
    MODE_VK_ONLY: "Только ВКонтакте",
    MODE_TG_ONLY: "Только Telegram",
    MODE_VK_AND_TG: "ВК + Telegram",
}

# All known attachment kinds for the filter UI.
ALL_ATTACHMENT_KINDS = [
    "photo", "sticker", "voice", "audio", "video",
    "video_note", "animation", "document", "gift",
]

# Attachment kinds relevant to each source type.
VK_ATTACHMENT_KINDS = [
    "photo", "sticker", "voice", "audio", "video",
    "animation", "document", "gift",
]
TG_ATTACHMENT_KINDS = [
    "photo", "sticker", "voice", "audio", "video",
    "video_note", "animation", "document",
]

# Human-readable labels for attachment kinds.
ATTACHMENT_LABELS = {
    "photo": "Фото",
    "sticker": "Стикеры",
    "voice": "Голосовые",
    "audio": "Аудио",
    "video": "Видео",
    "video_note": "Видеосообщения",
    "animation": "GIF",
    "document": "Документы",
    "gift": "Подарки (ВК)",
}


def normalize_path(path: str) -> str:
    """Accept absolute/relative paths and Windows backslashes."""
    if not path or not str(path).strip():
        return ""
    p = os.path.expandvars(os.path.expanduser(str(path).strip()))
    p = os.path.normpath(p)
    return p


# ---------------------------------------------------------------------------
#  Default structures
# ---------------------------------------------------------------------------

def default_attachments_filter() -> dict[str, bool]:
    """Execute the default attachments filter operation."""
    return {k: True for k in ALL_ATTACHMENT_KINDS}


def default_task() -> dict:
    """Execute the default task operation."""
    return {
        "name": "Задача 1",
        "mode": MODE_VK_AND_TG,
        "multichat": False,
        "multichat_bot": "",
        "target": {
            "chat_id": 0,
        },
        "sources": {
            "vk_exports": [],
            "vk_media_mirrors": [],
            "telegram_exports": [],
        },
        "bots": {},
        "sender_map": {
            "vk": {},
            "vk_default": "",
            "telegram": {},
            "telegram_default": "",
        },
        "display_names": {},
        "system_bot": "",
        "attachments_filter": default_attachments_filter(),
        "rate": {
            "min_interval_seconds": 1.5,
            "jitter_seconds": 0.4,
            "error_backoff_seconds": 5.0,
            "http_connect_timeout": 15,
            "http_read_timeout": 120,
        },
        "retry": {
            "media_download_attempts": 12,
            "media_retry_backoff_seconds": 5.0,
            "send_media_attempts": 6,
        },
        "behavior": {
            "send_date_headers": True,
            "send_section_headers": True,
            "placeholders_for_missing": True,
        },
    }


def default_settings() -> dict:
    """Execute the default settings operation."""
    return {"tasks": [default_task()]}


# ---------------------------------------------------------------------------
#  Merge / normalize
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Execute the deep merge operation."""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _migrate_legacy(data: dict) -> dict:
    """Convert old single-task format (no 'tasks' key) to multi-task."""
    if "tasks" in data:
        return data
    # Old format: top-level mode/target/sources/bots/sender_map/rate/retry/behavior
    task = copy.deepcopy(data)
    # Migrate old vk_json -> vk_exports
    if "sources" in task:
        src = task["sources"]
        if "vk_json" in src and "vk_exports" not in src:
            vk_json = src.pop("vk_json", "")
            if vk_json:
                src["vk_exports"] = [{"path": vk_json, "label": "ВК"}]
            else:
                src["vk_exports"] = []
    # Migrate old bots dict {key: token_string} -> keep as is (new format is same)
    task.setdefault("name", "Задача 1")
    task.setdefault("multichat", False)
    task.setdefault("multichat_bot", "")
    task.setdefault("display_names", {})
    task.setdefault("system_bot", "")
    task.setdefault("attachments_filter", default_attachments_filter())
    return {"tasks": [task]}


def normalize_task(data: dict) -> dict:
    """Fill defaults, normalize paths, coerce types for a single task."""
    t = _deep_merge(default_task(), data or {})

    t["name"] = (t.get("name") or "Задача").strip()
    t["mode"] = t.get("mode") or MODE_VK_AND_TG
    if t["mode"] not in MODES:
        t["mode"] = MODE_VK_AND_TG
    t["multichat"] = bool(t.get("multichat", False))
    t["multichat_bot"] = str(t.get("multichat_bot", "")).strip()

    # Target
    try:
        t["target"]["chat_id"] = int(t["target"]["chat_id"])
    except (TypeError, ValueError, KeyError):
        t.setdefault("target", {})["chat_id"] = 0

    # Sources — VK exports
    src = t.setdefault("sources", {})
    vk_exports = []
    for ex in src.get("vk_exports") or []:
        if not isinstance(ex, dict):
            continue
        path = normalize_path(ex.get("path", ""))
        if not path:
            continue
        label = (ex.get("label") or f"ВК {len(vk_exports) + 1}").strip()
        vk_exports.append({"path": path, "label": label})
    src["vk_exports"] = vk_exports

    # Sources — VK media mirrors
    mirrors = []
    for m in src.get("vk_media_mirrors") or []:
        if not isinstance(m, dict):
            continue
        cache = normalize_path(m.get("cache", ""))
        web = normalize_path(m.get("web", ""))
        if cache or web:
            mirrors.append({"cache": cache, "web": web})
    src["vk_media_mirrors"] = mirrors

    # Sources — Telegram exports
    exports = []
    for ex in src.get("telegram_exports") or []:
        if not isinstance(ex, dict):
            continue
        path = normalize_path(ex.get("path", ""))
        if not path:
            continue
        label = (ex.get("label") or f"Телеграм {len(exports) + 1}").strip()
        exports.append({"path": path, "label": label})
    src["telegram_exports"] = exports

    # Bots — {key: token} (ensure all values are strings)
    bots = {}
    for k, v in (t.get("bots") or {}).items():
        bots[str(k).strip()] = str(v).strip()
    t["bots"] = bots

    # Sender map — VK ids must be string keys (display as int)
    sm = t.setdefault("sender_map", {})
    vk_map = {}
    for k, v in (sm.get("vk") or {}).items():
        try:
            vk_map[str(int(k))] = str(v)
        except (TypeError, ValueError):
            pass
    sm["vk"] = vk_map
    sm.setdefault("vk_default", "")
    # TG sender map
    tg_map = {}
    for k, v in (sm.get("telegram") or {}).items():
        tg_map[str(k).strip().lower()] = str(v)
    sm["telegram"] = tg_map
    sm.setdefault("telegram_default", "")

    # Display names
    dn = {}
    for k, v in (t.get("display_names") or {}).items():
        dn[str(k).strip()] = str(v).strip()
    t["display_names"] = dn
    t["system_bot"] = str(t.get("system_bot", "")).strip()

    # Attachments filter
    af = t.get("attachments_filter") or {}
    full = default_attachments_filter()
    for k in full:
        full[k] = bool(af.get(k, True))
    t["attachments_filter"] = full

    return t


def normalize_settings(data: dict) -> dict:
    """Normalize the entire settings file (all tasks)."""
    data = _migrate_legacy(data or {})
    tasks = data.get("tasks") or [default_task()]
    data["tasks"] = [normalize_task(t) for t in tasks]
    if not data["tasks"]:
        data["tasks"] = [default_task()]
    return data


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------

def validate_task(t: dict) -> list[str]:
    """Return a list of human-readable problems for one task (empty == OK)."""
    t = normalize_task(t)
    errs: list[str] = []
    mode = t["mode"]

    # Chat ID
    if not t["target"]["chat_id"]:
        errs.append("Не указан Chat ID целевого чата.")

    # VK sources
    if mode in (MODE_VK_ONLY, MODE_VK_AND_TG):
        vk_exports = t["sources"]["vk_exports"]
        if not vk_exports:
            errs.append("Не добавлен ни один VK JSON экспорт.")
        else:
            for ex in vk_exports:
                if not os.path.isfile(ex["path"]):
                    errs.append(f"VK JSON не найден: {ex['path']}")

    # TG sources
    if mode in (MODE_TG_ONLY, MODE_VK_AND_TG):
        exports = t["sources"]["telegram_exports"]
        if not exports:
            errs.append("Добавьте хотя бы одну папку экспорта Telegram.")
        else:
            for ex in exports:
                p = ex["path"]
                if not os.path.isdir(p):
                    errs.append(f"Папка Telegram не найдена: {p}")
                elif not _looks_like_tg_export(p):
                    errs.append(f"В папке нет messages*.html: {p}")

    # Bots
    if not t["bots"]:
        errs.append("Не добавлен ни один бот.")
    else:
        for key, token in t["bots"].items():
            if not token:
                errs.append(f"Не указан токен для бота «{key}».")

    # Multichat
    if t["multichat"]:
        if t["multichat_bot"] and t["multichat_bot"] not in t["bots"]:
            errs.append(f"Бот мульти-чата «{t['multichat_bot']}» не найден в списке ботов.")

    # Rate
    try:
        float(t["rate"]["min_interval_seconds"])
    except (TypeError, ValueError, KeyError):
        errs.append("Пауза между сообщениями должна быть числом.")

    return errs


def validate_settings(data: dict) -> list[str]:
    """Validate all tasks. Returns problems for the first invalid task."""
    s = normalize_settings(data)
    for i, task in enumerate(s["tasks"]):
        errs = validate_task(task)
        if errs:
            prefix = f"[{task['name']}] " if len(s["tasks"]) > 1 else ""
            return [prefix + e for e in errs]
    return []


def _looks_like_tg_export(folder: str) -> bool:
    """Execute the looks like tg export operation."""
    try:
        for name in os.listdir(folder):
            if name.startswith("messages") and name.endswith(".html"):
                return True
    except OSError:
        return False
    return False


# ---------------------------------------------------------------------------
#  Load / save
# ---------------------------------------------------------------------------

def load_settings(path: str | None = None) -> dict:
    """Execute the load settings operation."""
    path = path or SETTINGS_FILE
    if not os.path.isfile(path):
        data = default_settings()
        save_settings(data, path)
        return data
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return normalize_settings(raw)


def save_settings(data: dict, path: str | None = None) -> str:
    """Execute the save settings operation."""
    path = path or SETTINGS_FILE
    s = normalize_settings(data)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
#  Apply to runtime config
# ---------------------------------------------------------------------------

def apply_task(task: dict | None = None, task_index: int = 0) -> dict:
    """Patch the live `config` module from a single task dict."""
    if task is None:
        s = load_settings()
        tasks = s.get("tasks", [])
        task = tasks[task_index] if task_index < len(tasks) else default_task()
    t = normalize_task(task)

    config.MODE = t["mode"]
    config.CHAT_ID = int(t["target"]["chat_id"])

    # Bots
    config.BOT_TOKENS = dict(t["bots"])
    config.SYSTEM_BOT = t["system_bot"] or (
        list(t["bots"].keys())[0] if t["bots"] else "")

    # VK exports
    config.VK_EXPORTS = list(t["sources"]["vk_exports"])
    config.VK_JSON = config.VK_EXPORTS[0]["path"] if config.VK_EXPORTS else ""
    config.VK_MEDIA_MIRRORS = [
        (m["cache"], m["web"]) for m in t["sources"]["vk_media_mirrors"]
    ]

    # TG exports
    exports = t["sources"]["telegram_exports"]
    config.TG_DIRS = [e["path"] for e in exports]
    config.TG_SECTION_LABELS = [e["label"] for e in exports]
    config.TG_DIR = config.TG_DIRS[0] if config.TG_DIRS else ""
    config.TG_FILES_DIR = os.path.join(config.TG_DIR, "files") if config.TG_DIR else ""

    # Sender map
    sm = t["sender_map"]
    config.VK_SENDER_MAP = dict(sm.get("vk") or {})
    config.VK_DEFAULT_SENDER = sm.get("vk_default") or (
        list(t["bots"].keys())[0] if t["bots"] else "")
    config.TG_SENDER_MAP = {str(k).lower(): v for k, v in (sm.get("telegram") or {}).items()}
    config.TG_DEFAULT_SENDER = sm.get("telegram_default") or (
        list(t["bots"].keys())[0] if t["bots"] else "")

    # Multichat
    config.MULTICHAT = bool(t["multichat"])
    config.MULTICHAT_BOT = t["multichat_bot"] or (
        list(t["bots"].keys())[0] if t["bots"] else "")
    config.DISPLAY_NAMES = dict(t.get("display_names") or {})

    # Attachment filter
    config.ATTACHMENTS_FILTER = dict(t.get("attachments_filter") or {})

    # Rate
    rate = t["rate"]
    config.MIN_INTERVAL_SECONDS = float(rate.get("min_interval_seconds", 1.5))
    config.JITTER_SECONDS = float(rate.get("jitter_seconds", 0.4))
    config.ERROR_BACKOFF_SECONDS = float(rate.get("error_backoff_seconds", 5.0))
    config.HTTP_TIMEOUT = (
        int(rate.get("http_connect_timeout", 15)),
        int(rate.get("http_read_timeout", 120)),
    )

    # Retry
    retry = t["retry"]
    config.MEDIA_DOWNLOAD_ATTEMPTS = int(retry.get("media_download_attempts", 12))
    config.MEDIA_RETRY_BACKOFF_SECONDS = float(retry.get("media_retry_backoff_seconds", 5.0))
    config.SEND_MEDIA_ATTEMPTS = int(retry.get("send_media_attempts", 6))

    # Behavior
    beh = t["behavior"]
    config.SEND_DATE_HEADERS = bool(beh.get("send_date_headers", True))
    config.SEND_SECTION_HEADERS = bool(beh.get("send_section_headers", True))
    config.PLACEHOLDERS_FOR_MISSING = bool(beh.get("placeholders_for_missing", True))

    # Per-task state/results files
    sfx = f"_{task_index}" if task_index > 0 else ""
    config.STATE_FILE = os.path.join(EXPORTER_DIR, f"state{sfx}.json")
    config.RESULTS_FILE = os.path.join(EXPORTER_DIR, f"results{sfx}.jsonl")
    config.NOT_SENT_FILE = os.path.join(EXPORTER_DIR, f"not_sent{sfx}.log")

    # Invalidate cached VK media map when paths change
    try:
        import media_map
        media_map.reset()
    except Exception:
        pass

    # Reset bot cache (tokens may have changed)
    try:
        import telegram_client
        telegram_client.reset_bots()
    except Exception:
        pass

    return t


# Backward-compatible aliases
def apply_settings(data: dict | None = None) -> dict:
    """Legacy wrapper: applies the first task from a settings dict."""
    if data is None:
        return apply_task()
    s = normalize_settings(data)
    return apply_task(s["tasks"][0], 0)


def load_and_apply(path: str | None = None) -> dict:
    """Execute the load and apply operation."""
    s = load_settings(path)
    if s["tasks"]:
        apply_task(s["tasks"][0], 0)
    return s


def task_summary(t_data: dict) -> str:
    """One-line summary for a task."""
    t_data = normalize_task(t_data)
    mode = t(f"mode.{t_data['mode']}")
    chat = t_data["target"]["chat_id"]
    n_vk = len(t_data["sources"]["vk_exports"])
    n_tg = len(t_data["sources"]["telegram_exports"])
    n_bots = len(t_data["bots"])
    
    parts = [f"{t('gui.summary_mode')} {mode}", f"{t('gui.summary_chat')} {chat or '—'}"]
    if t_data["mode"] in (MODE_VK_ONLY, MODE_VK_AND_TG):
        parts.append(f"{t('gui.summary_vk')} {n_vk}")
    if t_data["mode"] in (MODE_TG_ONLY, MODE_VK_AND_TG):
        parts.append(f"{t('gui.summary_tg')} {n_tg}")
    parts.append(f"{t('gui.summary_bots')} {n_bots}")
    if t_data["multichat"]:
        parts.append(t("gui.summary_multichat"))
    return " · ".join(parts)


def settings_summary(s: dict | None = None) -> str:
    """Summary for the header bar."""
    s = normalize_settings(s or load_settings())
    n = len(s["tasks"])
    if n == 1:
        return task_summary(s["tasks"][0])
    return t("gui.summary_tasks").format(n=n)
