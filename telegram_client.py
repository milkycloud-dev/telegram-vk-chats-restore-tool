"""Telegram Bot API client with shared pacing, infinite network retry, and
responsive pause / stop / skip via the global CONTROL object."""
import os
import random
import threading
import time

import requests

import config
from control import CONTROL, SkipRequested, StopRequested

_API = "https://api.telegram.org/bot{token}/{method}"

# Shared pacing state: both bots write to the SAME chat, so the flood limit is
# shared. We serialize all sends through one timestamp.
_last_send_ts = [0.0]


class TelegramError(Exception):
    """Execute the TelegramError operation."""
    pass


# A lightweight reachability probe. Any HTTP reply (even an error page) means the
# network is up; only a transport-level failure means there is no connectivity.
_PROBE_URL = "https://api.telegram.org"
_probe_session = requests.Session()


def _network_up() -> bool:
    """Execute the network up operation."""
    try:
        _probe_session.head(_PROBE_URL, timeout=(5, 5))
        return True
    except Exception:
        return False


def _interruptible_sleep(seconds: float):
    """Sleep while staying responsive to skip/stop; honor pause."""
    CONTROL.interruptible_sleep(seconds, allow_skip=True)


def _pace():
    """Execute the pace operation."""
    CONTROL.wait_if_paused()
    if CONTROL.stop_requested():
        raise StopRequested()
    now = time.time()
    wait = config.MIN_INTERVAL_SECONDS - (now - _last_send_ts[0])
    extra = random.uniform(0, config.JITTER_SECONDS) if config.JITTER_SECONDS else 0
    total = max(0.0, wait) + extra
    if total > 0:
        # Pacing sleep is interruptible by stop/pause but NOT by skip (skip only
        # aborts an in-flight upload, not the inter-message delay).
        end = time.time() + total
        while True:
            CONTROL.wait_if_paused()
            if CONTROL.stop_requested():
                raise StopRequested()
            rem = end - time.time()
            if rem <= 0:
                break
            time.sleep(min(0.15, rem))
    _last_send_ts[0] = time.time()


class Bot:
    """Execute the Bot operation."""
    def __init__(self, token: str, name: str):
        """Initialize the instance."""
        self.token = token
        self.name = name
        self._s = requests.Session()

    def _post_async(self, url, data, files):
        """Run the blocking POST in a worker thread so we can react to skip/stop
        within ~0.15s even while a large upload is hung."""
        box = {}

        def worker():
            """Execute the worker operation."""
            try:
                box["resp"] = self._s.post(url, data=data, files=files,
                                           timeout=config.HTTP_TIMEOUT)
            except Exception as e:  # noqa: BLE001
                box["err"] = e

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        while th.is_alive():
            if CONTROL.skip_requested():
                raise SkipRequested()
            if CONTROL.stop_requested():
                raise StopRequested()
            th.join(0.15)
        if "err" in box:
            raise box["err"]
        return box["resp"]

    def _rewind(self, files):
        # Re-seek uploaded file handles before a retry.
        """Execute the rewind operation."""
        if not files:
            return
        for v in files.values():
            try:
                v.seek(0)
            except Exception:
                pass

    def _call(self, method: str, data: dict, files: dict | None = None,
              max_net_attempts: int | None = None):
        """Send one API call. Network/5xx errors are retried with back-off.

        If `max_net_attempts` is set (used for media uploads), give up after that
        many failed attempts and raise TelegramError so the caller can fall back
        to a placeholder — this prevents a hanging video from retrying forever.
        429 flood-waits never count toward the limit. With `max_net_attempts`
        None (text messages) retries are infinite."""
        url = _API.format(token=self.token, method=method)
        net_fails = 0
        while True:
            _pace()
            try:
                resp = self._post_async(url, data, files)
            except (requests.RequestException, OSError) as e:
                self._rewind(files)
                CONTROL.stats.inc("retries")
                # Distinguish a real outage (no connectivity at all) from a
                # request that fails while the network is otherwise up.
                if not _network_up():
                    # No internet -> wait INFINITELY for it to come back and do
                    # NOT consume the per-attachment attempt budget.
                    CONTROL.stats.log_event(
                        "НЕТ СЕТИ", f"{method}: нет соединения, ждём сеть ({type(e).__name__})")
                    _interruptible_sleep(config.ERROR_BACKOFF_SECONDS)
                    continue
                # Network is up, but THIS upload keeps failing (e.g. a heavy video
                # the server aborts). Count it; skip after max_net_attempts.
                net_fails += 1
                CONTROL.stats.log_event(
                    "СЕТЬ", f"{method}: {type(e).__name__}: {e} (попытка {net_fails})")
                if max_net_attempts and net_fails >= max_net_attempts:
                    CONTROL.stats.log_event(
                        "ОТКАЗ", f"{method}: пропуск вложения после {net_fails} неудачных попыток")
                    raise TelegramError(f"{method}: gave up after {net_fails} network failures")
                _interruptible_sleep(config.ERROR_BACKOFF_SECONDS)
                continue

            try:
                payload = resp.json()
            except Exception:
                payload = {}

            if resp.status_code == 200 and payload.get("ok"):
                return payload["result"]

            # Flood control: always wait and retry (does NOT count as a failure).
            if resp.status_code == 429:
                retry_after = (payload.get("parameters", {}) or {}).get("retry_after", 5)
                CONTROL.stats.inc("flood_waits")
                CONTROL.stats.log_event(
                    "429", f"{method}: флуд-контроль, ожидание {retry_after}s")
                self._rewind(files)
                _interruptible_sleep(float(retry_after) + 1.0)
                continue

            # Transient server errors: retry (bounded for media uploads).
            if resp.status_code >= 500:
                net_fails += 1
                CONTROL.stats.inc("retries")
                CONTROL.stats.log_event(
                    "СЕРВЕР", f"{method}: HTTP {resp.status_code} (попытка {net_fails})")
                self._rewind(files)
                if max_net_attempts and net_fails >= max_net_attempts:
                    CONTROL.stats.log_event(
                        "ОТКАЗ", f"{method}: пропуск вложения после {net_fails} попыток (сервер)")
                    raise TelegramError(f"{method}: gave up after {net_fails} server errors")
                _interruptible_sleep(config.ERROR_BACKOFF_SECONDS)
                continue

            # 4xx (bad request etc.) are permanent: surface so caller can skip.
            desc = payload.get("description", resp.text)
            CONTROL.stats.log_event("ОШИБКА", f"{method} [{resp.status_code}]: {desc}")
            raise TelegramError(f"{method} failed [{resp.status_code}]: {desc}")

    # --- public send methods --------------------------------------------------
    def send_message(self, text: str, **kw):
        """Execute the send message operation."""
        data = {"chat_id": config.CHAT_ID, "text": text,
                "disable_web_page_preview": True}
        data.update(kw)
        return self._call("sendMessage", data)

    def _send_file(self, method: str, field: str, path_or_url: str, data: dict):
        # Local file -> multipart upload; URL/file_id -> plain field.
        # Media uploads are capped so a hanging file is skipped, not retried forever.
        """Execute the send file operation."""
        cap = config.SEND_MEDIA_ATTEMPTS
        if path_or_url and os.path.exists(path_or_url):
            with open(path_or_url, "rb") as fh:
                return self._call(method, data, files={field: fh}, max_net_attempts=cap)
        data = dict(data)
        data[field] = path_or_url
        return self._call(method, data, max_net_attempts=cap)

    def send_photo(self, photo: str, caption: str = ""):
        """Execute the send photo operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        return self._send_file("sendPhoto", "photo", photo, data)

    def send_sticker(self, sticker: str):
        """Execute the send sticker operation."""
        return self._send_file("sendSticker", "sticker", sticker,
                               {"chat_id": config.CHAT_ID})

    def send_voice(self, voice: str, caption: str = "", duration: int = 0):
        """Execute the send voice operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        if duration:
            data["duration"] = duration
        return self._send_file("sendVoice", "voice", voice, data)

    def send_audio(self, audio: str, caption: str = "", title: str = "",
                   performer: str = "", duration: int = 0):
        """Execute the send audio operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        if title:
            data["title"] = title
        if performer:
            data["performer"] = performer
        if duration:
            data["duration"] = duration
        return self._send_file("sendAudio", "audio", audio, data)

    def send_video(self, video: str, caption: str = "", duration: int = 0):
        """Execute the send video operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        if duration:
            data["duration"] = duration
        return self._send_file("sendVideo", "video", video, data)

    def send_video_note(self, video_note: str):
        """Execute the send video note operation."""
        return self._send_file("sendVideoNote", "video_note", video_note,
                               {"chat_id": config.CHAT_ID})

    def send_animation(self, animation: str, caption: str = ""):
        """Execute the send animation operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        return self._send_file("sendAnimation", "animation", animation, data)

    def send_document(self, document: str, caption: str = ""):
        """Execute the send document operation."""
        data = {"chat_id": config.CHAT_ID}
        if caption:
            data["caption"] = caption[:1024]
        return self._send_file("sendDocument", "document", document, data)

    def get_me(self):
        """Retrieve the me."""
        return self._call("getMe", {})


_bots: dict[str, Bot] = {}


def get_bot(key: str) -> Bot:
    """Retrieve the bot."""
    if key not in _bots:
        token = config.BOT_TOKENS.get(key, "")
        if not token:
            raise TelegramError(f"No token configured for bot '{key}'")
        _bots[key] = Bot(token, key)
    return _bots[key]


def reset_bots():
    """Clear the bot cache.  Call when switching tasks (tokens may differ)."""
    _bots.clear()
