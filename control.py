"""Shared run-time control + statistics, used by the sender, the client and the
GUI. A single global CONTROL instance coordinates pause / stop / skip and holds
live counters that the GUI polls."""
import threading
import time


class StopRequested(Exception):
    """Raised inside a blocking send when the user asks to stop the whole run."""


class SkipRequested(Exception):
    """Raised inside a blocking send when the user asks to skip the current item."""


# Counter categories shown in the GUI.
TYPE_KEYS = ["text", "photo", "sticker", "voice", "audio", "video",
             "video_note", "animation", "document", "header"]


class Stats:
    """Execute the Stats operation."""
    def __init__(self):
        """Initialize the instance."""
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        """Execute the reset operation."""
        with self._lock:
            self.total = 0
            self.index = 0           # actions processed so far
            self.phase = "—"
            self.start_ts = None
            self.counts = {k: 0 for k in TYPE_KEYS}
            self.placeholders = 0
            self.errors = 0
            self.skipped = 0
            self.retries = 0         # network retry attempts
            self.last_error = ""
            self.current = ""        # description of current action
            # extended stats
            self.downloads = 0       # media files downloaded this session
            self.downloaded_bytes = 0
            self.conversions = 0     # mp3->opus / png->webp conversions
            self.flood_waits = 0     # 429 flood-control waits
            self.current_file = ""   # file/url currently being handled
            self.current_kind = ""   # attachment kind currently handled
            self.current_sender = "" # bot currently sending
            self.vk_total = 0
            self.tg_total = 0
            self.vk_done = 0
            self.tg_done = 0
            # Chronological error/event log (429, network, server, download).
            self.event_log = []

    def start(self, total):
        """Execute the start operation."""
        with self._lock:
            self.total = total
            self.start_ts = time.time()

    def inc(self, key, n=1):
        """Execute the inc operation."""
        with self._lock:
            if key in self.counts:
                self.counts[key] += n
            else:
                setattr(self, key, getattr(self, key, 0) + n)

    def set(self, **kw):
        """Execute the set operation."""
        with self._lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def log_event(self, level: str, message: str):
        """Record an error/event with a wall-clock timestamp for the GUI error
        window. `level` is a short tag (e.g. '429', 'СЕТЬ', 'СЕРВЕР')."""
        with self._lock:
            self.event_log.append({"ts": time.time(), "level": level,
                                   "msg": str(message)[:500]})
            if len(self.event_log) > 2000:
                self.event_log = self.event_log[-2000:]
            self.last_error = f"{level}: {message}"

    def events_snapshot(self) -> list:
        """Execute the events snapshot operation."""
        with self._lock:
            return list(self.event_log)

    def snapshot(self) -> dict:
        """Execute the snapshot operation."""
        with self._lock:
            elapsed = (time.time() - self.start_ts) if self.start_ts else 0.0
            done = self.index
            rate = (done / elapsed) if elapsed > 0 else 0.0
            remaining = max(0, self.total - done)
            eta = (remaining / rate) if rate > 0 else 0.0
            sent = sum(self.counts.values())
            return {
                "total": self.total, "index": self.index, "phase": self.phase,
                "elapsed": elapsed, "rate": rate, "eta": eta,
                "counts": dict(self.counts), "sent": sent,
                "placeholders": self.placeholders, "errors": self.errors,
                "skipped": self.skipped, "retries": self.retries,
                "last_error": self.last_error, "current": self.current,
                "downloads": self.downloads,
                "downloaded_bytes": self.downloaded_bytes,
                "conversions": self.conversions, "flood_waits": self.flood_waits,
                "current_file": self.current_file, "current_kind": self.current_kind,
                "current_sender": self.current_sender,
                "vk_total": self.vk_total, "tg_total": self.tg_total,
                "vk_done": self.vk_done, "tg_done": self.tg_done,
            }


class Control:
    """Execute the Control operation."""
    def __init__(self):
        """Initialize the instance."""
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._skip = threading.Event()
        self.stats = Stats()

    # stop -------------------------------------------------------------
    def request_stop(self):
        """Execute the request stop operation."""
        self._stop.set()
        self._pause.clear()  # unblock any pause wait

    def stop_requested(self) -> bool:
        """Execute the stop requested operation."""
        return self._stop.is_set()

    def clear_stop(self):
        """Execute the clear stop operation."""
        self._stop.clear()

    # pause ------------------------------------------------------------
    def pause(self):
        """Execute the pause operation."""
        self._pause.set()

    def resume(self):
        """Execute the resume operation."""
        self._pause.clear()

    def is_paused(self) -> bool:
        """Check if paused."""
        return self._pause.is_set()

    def wait_if_paused(self):
        """Execute the wait if paused operation."""
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(0.1)

    # skip -------------------------------------------------------------
    def request_skip(self):
        """Execute the request skip operation."""
        self._skip.set()

    def skip_requested(self) -> bool:
        """Execute the skip requested operation."""
        return self._skip.is_set()

    def clear_skip(self):
        """Execute the clear skip operation."""
        self._skip.clear()

    def interruptible_sleep(self, seconds: float, allow_skip: bool = True):
        """Sleep `seconds` while staying responsive: honors pause, and raises
        StopRequested / SkipRequested if those are requested."""
        end = time.time() + seconds
        while True:
            self.wait_if_paused()
            if self._stop.is_set():
                raise StopRequested()
            if allow_skip and self._skip.is_set():
                raise SkipRequested()
            remaining = end - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.15, remaining))

    def checkpoints(self):
        """Raise if stop/skip requested; honor pause. Call between operations."""
        if self._stop.is_set():
            raise StopRequested()
        self.wait_if_paused()
        if self._stop.is_set():
            raise StopRequested()
        if self._skip.is_set():
            raise SkipRequested()


CONTROL = Control()
