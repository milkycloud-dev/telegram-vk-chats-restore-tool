"""Media download + sticker conversion helpers."""
import hashlib
import os
import subprocess
from urllib.parse import urlparse

import requests
from PIL import Image

import config
from control import CONTROL

# HTTP statuses that mean the resource is permanently gone (don't wait/retry).
_PERMANENT = {400, 401, 403, 404, 410, 451}

# Only VK's own CDN/media hosts may be downloaded. Anything else (a YouTube
# link, a webpage, an external file the user merely *linked* in chat) is NEVER
# fetched — such content stays as a text link in the recreated chat.
_VK_HOST_SUFFIXES = (
    "userapi.com", "vk.com", "vk.me", "vk-cdn.net", "vkcdn.net",
    "vkuseraudio.net", "vkuservideo.net", "vkuserlive.net", "vkuserphoto.net",
    "mycdn.me",
)


def _is_vk_media_url(url: str) -> bool:
    """True only for URLs hosted on VK's own media CDNs."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return any(host == s or host.endswith("." + s) for s in _VK_HOST_SUFFIXES)

_FFMPEG = None


def _ffmpeg() -> str | None:
    global _FFMPEG
    if _FFMPEG is None:
        try:
            import imageio_ffmpeg
            _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            _FFMPEG = ""
    return _FFMPEG or None

_session = requests.Session()
_session.headers.update({"User-Agent": config.HTTP_UA})


def _cache_path(key: str, ext: str) -> str:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    return os.path.join(config.CACHE_DIR, f"{h}.{ext.lstrip('.')}")


def download(url: str, ext: str = "bin") -> str | None:
    """Download `url` to the cache and return the local path.

    Uses a BOUNDED number of attempts: a per-URL failure (SSLError, refused,
    timeout, 5xx) is retried a few times and then gives up (returns None) so the
    run never freezes on a bad VK link. We rely mainly on local copies; a None
    result becomes a labeled placeholder. Returns None immediately for resources
    that are permanently gone (HTTP 4xx)."""
    if not url:
        return None
    # Never reach out to external hosts: links sent in chat are kept as text.
    if not _is_vk_media_url(url):
        CONTROL.stats.log_event("ССЫЛКА", f"внешняя ссылка не скачивается: {url[:140]}")
        return None
    path = _cache_path(url, ext)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    attempts = max(1, config.MEDIA_DOWNLOAD_ATTEMPTS)
    for attempt in range(1, attempts + 1):
        try:
            with _session.get(url, stream=True, timeout=config.HTTP_TIMEOUT) as r:
                if r.status_code in _PERMANENT:
                    CONTROL.stats.log_event("ЗАГРУЗКА", f"ВК-медиа недоступно (HTTP {r.status_code})")
                    return None  # gone for good
                if r.status_code != 200:
                    CONTROL.stats.inc("retries")
                    CONTROL.stats.set(
                        last_error=f"загрузка: HTTP {r.status_code} (попытка {attempt}/{attempts})")
                    if attempt < attempts:
                        CONTROL.interruptible_sleep(config.MEDIA_RETRY_BACKOFF_SECONDS)
                        continue
                    CONTROL.stats.log_event("ЗАГРУЗКА", f"ВК-медиа: HTTP {r.status_code} после {attempts} попыток")
                    return None
                tmp = path + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(64 * 1024):
                        if chunk:
                            f.write(chunk)
                size = os.path.getsize(tmp)
                if size == 0:
                    os.remove(tmp)
                    return None
                os.replace(tmp, path)
                CONTROL.stats.inc("downloads")
                CONTROL.stats.inc("downloaded_bytes", size)
                return path
        except (requests.RequestException, OSError) as e:
            CONTROL.stats.inc("retries")
            CONTROL.stats.set(
                last_error=f"загрузка не удалась [{type(e).__name__}] (попытка {attempt}/{attempts})")
            if attempt < attempts:
                CONTROL.interruptible_sleep(config.MEDIA_RETRY_BACKOFF_SECONDS)
                continue
            CONTROL.stats.log_event(
                "ЗАГРУЗКА", f"ВК-медиа не скачано [{type(e).__name__}] после {attempts} попыток")
            return None
    return None


def to_sticker_webp(url: str) -> str | None:
    """Download an image (VK sticker is PNG) and convert to a 512px webp suitable
    for sendSticker. Returns the local webp path or None."""
    src = download(url, "src")
    if not src:
        return None
    out = _cache_path(url + "#sticker", "webp")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    try:
        with Image.open(src) as im:
            im = im.convert("RGBA")
            w, h = im.size
            scale = 512 / max(w, h)
            if scale < 1:
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                               Image.LANCZOS)
            im.save(out, "WEBP", lossless=True)
        CONTROL.stats.inc("conversions")
        return out
    except Exception:
        return None


def mp3_to_opus(src: str) -> str | None:
    """Convert an mp3 voice file to ogg/opus so it can be sent as a real Telegram
    voice message. Returns the ogg path, or None if conversion is unavailable."""
    if not src or not os.path.exists(src):
        return None
    ff = _ffmpeg()
    if not ff:
        return None
    out = _cache_path(os.path.abspath(src) + "#opus", "ogg")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    try:
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", src,
                        "-c:a", "libopus", "-b:a", "32k", out],
                       check=True)
        if os.path.getsize(out) > 0:
            CONTROL.stats.inc("conversions")
            return out
    except Exception:
        return None
    return None
