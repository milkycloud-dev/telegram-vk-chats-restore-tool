"""Main orchestrator: replay VK chat, then Telegram chat, into the target
Telegram supergroup via bots.

Exposes a reusable `run()` that the GUI drives; also works as a CLI.
Supports resume, pause/stop/skip and live statistics via control.CONTROL.
"""
import argparse
import datetime as dt
import json
import os
import re

import config
import sender as snd
import tg_parser
import vk_parser
from control import CONTROL, SkipRequested, StopRequested
from telegram_client import get_bot, TelegramError


_RU_MONTHS_GEN = {1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                  5: "мая", 6: "июня", 7: "июля", 8: "августа",
                  9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"}

# Map English + Russian month names (any case) to a month number.
_MONTH_TO_NUM = {}
for _i, _en in enumerate(["january", "february", "march", "april", "may", "june",
                          "july", "august", "september", "october", "november",
                          "december"], 1):
    _MONTH_TO_NUM[_en] = _i
for _i, _ru in enumerate(["январь", "февраль", "март", "апрель", "май", "июнь",
                          "июль", "август", "сентябрь", "октябрь", "ноябрь",
                          "декабрь"], 1):
    _MONTH_TO_NUM[_ru] = _i
for _i, _ru in enumerate(["января", "февраля", "марта", "апреля", "мая", "июня",
                          "июля", "августа", "сентября", "октября", "ноября",
                          "декабря"], 1):
    _MONTH_TO_NUM[_ru] = _i


def _ru_date(year: int, month: int, day: int) -> str:
    """Execute the ru date operation."""
    return f"{day} {_RU_MONTHS_GEN.get(month, '')} {year}".replace("  ", " ").strip()


def default_log(msg: str):
    """Execute the default log operation."""
    line = f"{dt.datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    try:
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _vk_day(ts: int) -> str:
    """Execute the vk day operation."""
    if not ts:
        return ""
    d = dt.datetime.fromtimestamp(ts, dt.UTC)
    return _ru_date(d.year, d.month, d.day)


def _ru_day_from_label(label: str) -> str:
    """Convert a Telegram export day label (e.g. '28 June 2020') to Russian."""
    if not label:
        return label
    m = re.search(r"(\d{1,2})\s+([A-Za-zА-Яа-яёЁ]+)\s+(\d{4})", label)
    if not m:
        return label
    day, mon, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    num = _MONTH_TO_NUM.get(mon)
    if not num:
        return label
    return _ru_date(year, num, day)


def _get_system_bot():
    """Return the bot used for date headers and section separators."""
    key = config.SYSTEM_BOT
    if not key:
        # Fallback: first available bot
        keys = list(config.BOT_TOKENS.keys())
        if not keys:
            raise TelegramError("No bots configured")
        key = keys[0]
    return get_bot(key)


def build_actions(log=default_log):
    """Return a flat list of actions: ('msg', text) headers or ('ev', Event)."""
    actions = []
    mode = getattr(config, "MODE", "vk_and_tg")

    if mode in ("vk_only", "vk_and_tg"):
        vk_exports = getattr(config, "VK_EXPORTS", [])
        if not vk_exports:
            # Legacy fallback to VK_JSON
            if config.VK_JSON and os.path.isfile(config.VK_JSON):
                vk_exports = [{"path": config.VK_JSON, "label": "ВК"}]
            else:
                log("! No VK exports configured — skipping VK section.")

        for vk_idx, vk_export in enumerate(vk_exports):
            vk_path = vk_export["path"]
            vk_label = vk_export.get("label", f"ВК {vk_idx + 1}")
            if not os.path.isfile(vk_path):
                log(f"! VK JSON not found: {vk_path}")
                continue
            log(f"Parsing VK export [{vk_label}]: {vk_path}")
            vk_events = vk_parser.parse(vk_path)
            log(f"  VK events: {len(vk_events)}")
            if config.SEND_SECTION_HEADERS:
                actions.append(("msg", f"━━━━━━━━━━━━━━\n📨 {vk_label}\n━━━━━━━━━━━━━━"))
            prev = None
            for e in vk_events:
                day = _vk_day(e.date)
                if config.SEND_DATE_HEADERS and day and day != prev:
                    actions.append(("date", f"📅 {day}"))
                    prev = day
                actions.append(("ev", e))

    if mode in ("tg_only", "vk_and_tg"):
        tg_dirs = config.TG_DIRS or []
        if not tg_dirs:
            log("! No Telegram export folders configured.")
        for idx, tg_dir in enumerate(tg_dirs):
            label = (config.TG_SECTION_LABELS[idx]
                     if idx < len(config.TG_SECTION_LABELS) else f"Телеграм {idx + 1}")
            if not os.path.isdir(tg_dir):
                log(f"! Telegram folder missing: {tg_dir}")
                continue
            log(f"Parsing Telegram [{label}]: {tg_dir}")
            tg_events = tg_parser.parse(tg_dir)
            log(f"  events: {len(tg_events)}")
            if config.SEND_SECTION_HEADERS:
                actions.append(("msg", f"━━━━━━━━━━━━━━\n💬 {label}\n━━━━━━━━━━━━━━"))
            prev = None
            phase_label = label.title()
            for e in tg_events:
                e.chat_label = phase_label
                day = _ru_day_from_label(e.day_label)
                if config.SEND_DATE_HEADERS and day and day != prev:
                    actions.append(("date", f"📅 {day}"))
                    prev = day
                actions.append(("ev", e))

    return actions


def load_state() -> int:
    """Execute the load state operation."""
    if os.path.exists(config.STATE_FILE):
        try:
            return int(json.load(open(config.STATE_FILE))["index"])
        except Exception:
            return 0
    return 0


def save_state(index: int):
    """Execute the save state operation."""
    tmp = config.STATE_FILE + ".tmp"
    json.dump({"index": index}, open(tmp, "w"))
    os.replace(tmp, config.STATE_FILE)


def _event_status(result: dict) -> str:
    """Execute the event status operation."""
    if result["error"]:
        return "error"
    has_sent = bool(result["sent"]) or result["text"]
    if result["skipped"]:
        return "partial" if has_sent else "skipped"
    if result["placeholder"]:
        return "partial" if has_sent else "placeholder"
    if has_sent:
        return "sent"
    return "empty"


class Ledger:
    """Append-only record of what was sent and what wasn't."""

    def __init__(self, reset: bool):
        """Initialize the instance."""
        mode = "w" if reset else "a"
        self._res = open(config.RESULTS_FILE, mode, encoding="utf-8")
        self._not = open(config.NOT_SENT_FILE, mode, encoding="utf-8")
        self._n = 0

    def record(self, i: int, action, result):
        """Execute the record operation."""
        kind, payload = action
        if kind in ("msg", "date"):
            entry = {"i": i, "t": kind,
                     "status": "sent" if result.get("ok") else "error"}
        else:
            e = payload
            status = _event_status(result)
            entry = {"i": i, "t": "event", "src": e.source, "sender": e.sender,
                     "date": e.date, "status": status,
                     "sent": result["sent"], "placeholder": result["placeholder"],
                     "skipped": result["skipped"], "errors": result["error"],
                     "text": result["text"]}
            if status in ("placeholder", "skipped", "error", "partial"):
                when = (dt.datetime.fromtimestamp(e.date, dt.UTC).isoformat()
                        if e.date else (payload.day_label or "?"))
                preview = (e.text or "").replace("\n", " ")[:80]
                problem = (result["error"] or result["skipped"] or result["placeholder"])
                self._not.write(
                    f"#{i}\t{status}\t{e.source}\t{e.sender}\t{when}\t"
                    f"{','.join(problem)}\t{preview}\n")
        self._res.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._n += 1
        if self._n % 50 == 0:
            self.flush()

    def flush(self):
        """Execute the flush operation."""
        self._res.flush()
        self._not.flush()

    def close(self):
        """Execute the close operation."""
        try:
            self.flush()
            self._res.close()
            self._not.close()
        except Exception:
            pass


def _preview(action) -> tuple[str, str]:
    """Return (phase, short description) for the stats panel."""
    kind, payload = action
    if kind == "date":
        return "", payload.replace("\n", " ")[:60]
    if kind == "msg":
        if "ВКОНТАКТЕ" in payload or "📨" in payload:
            lbl = payload.split("📨")[-1].strip().splitlines()[0].strip() if "📨" in payload else "ВК"
            return lbl, f"── секция {lbl} ──"
        if "ТЕЛЕГРАМ" in payload or "💬" in payload:
            lbl = payload.split("💬")[-1].strip().splitlines()[0].strip().title() if "💬" in payload else "ТГ"
            return lbl, f"── секция {lbl} ──"
        return "", payload.replace("\n", " ")[:60]
    e = payload
    phase = "ВКонтакте" if e.source == "vk" else (e.chat_label or "Телеграм")
    desc = (e.text or "").replace("\n", " ")[:60]
    if not desc and e.attachments:
        desc = f"[{e.attachments[0].kind}]"
    return phase, desc or "(пусто)"


def run(actions=None, reset=False, limit=0, log=default_log):
    """Run the replay. Returns the index reached. Honors CONTROL."""
    CONTROL.clear_stop()
    if actions is None:
        actions = build_actions(log)
    total = len(actions)

    start = 0 if reset else load_state()
    if reset:
        save_state(0)
    CONTROL.stats.start(total)
    vk_total = sum(1 for k, p in actions if k == "ev" and p.source == "vk")
    tg_total = sum(1 for k, p in actions if k == "ev" and p.source == "tg")
    vk_done = sum(1 for k, p in actions[:start] if k == "ev" and p.source == "vk")
    tg_done = sum(1 for k, p in actions[:start] if k == "ev" and p.source == "tg")
    CONTROL.stats.set(index=start, vk_total=vk_total, tg_total=tg_total,
                      vk_done=vk_done, tg_done=tg_done)
    log(f"Total actions: {total}; starting at #{start}")

    system_bot = _get_system_bot()
    ledger = Ledger(reset=reset)
    last_phase = ""
    processed = 0
    stopped = False
    try:
        for i in range(start, total):
            if CONTROL.stop_requested():
                log("Stopped by user.")
                stopped = True
                break
            CONTROL.wait_if_paused()
            if CONTROL.stop_requested():
                log("Stopped by user.")
                stopped = True
                break
            # A skip clicked while idle has nothing to skip -> clear it.
            if CONTROL.skip_requested():
                CONTROL.clear_skip()

            phase, desc = _preview(actions[i])
            if phase:
                last_phase = phase
            CONTROL.stats.set(phase=last_phase or "—", current=desc)

            kind, payload = actions[i]
            result = {"ok": False, "text": False, "sent": [], "placeholder": [],
                      "skipped": [], "error": []}
            try:
                if kind in ("date", "msg"):
                    # All service / non-dialog messages go through the system bot.
                    system_bot.send_message(payload)
                    CONTROL.stats.inc("header")
                    result["ok"] = True
                else:
                    result = snd.send_event(payload)
            except StopRequested:
                log("Stopped by user.")
                stopped = True
                break
            except SkipRequested:
                CONTROL.clear_skip()
                CONTROL.stats.inc("skipped")
                result["skipped"].append(kind)
            except TelegramError as e:
                CONTROL.stats.inc("errors")
                CONTROL.stats.set(last_error=str(e))
                result["error"].append(str(e))
                log(f"! error at #{i}: {e}")
            except Exception as e:  # noqa: BLE001
                # Never let an unexpected error stop the whole run.
                CONTROL.stats.inc("errors")
                CONTROL.stats.set(last_error=str(e))
                result["error"].append(str(e))
                log(f"! unexpected at #{i}: {e}")

            ledger.record(i, actions[i], result)
            save_state(i + 1)
            CONTROL.stats.set(index=i + 1)
            if kind == "ev":
                if payload.source == "vk":
                    CONTROL.stats.inc("vk_done")
                else:
                    CONTROL.stats.inc("tg_done")
            processed += 1
            if i % 100 == 0:
                log(f"progress {i}/{total}")
            if limit and processed >= limit:
                log(f"Reached limit {limit}; stopping at #{i + 1}.")
                stopped = True
                break
    finally:
        ledger.close()

    if not stopped:
        log("DONE. Full dialog replayed.")
        CONTROL.stats.set(phase="Готово")

    return CONTROL.stats.snapshot()["index"]


def main():
    """Execute the main operation."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="ignore saved progress")
    ap.add_argument("--limit", type=int, default=0, help="send at most N then stop")
    ap.add_argument("--dry-run", action="store_true", help="parse and count only")
    ap.add_argument("--task", type=int, default=0, help="task index (default 0)")
    args = ap.parse_args()

    # Apply the selected task
    from settings_manager import load_settings, apply_task
    s = load_settings()
    tasks = s.get("tasks", [])
    if args.task >= len(tasks):
        default_log(f"Task index {args.task} out of range (have {len(tasks)} tasks).")
        return
    apply_task(tasks[args.task], args.task)

    actions = build_actions()
    default_log(f"Total actions to send: {len(actions)}")
    if args.dry_run:
        default_log("Dry run complete (nothing sent).")
        return
    try:
        run(actions, reset=args.reset, limit=args.limit)
    except KeyboardInterrupt:
        CONTROL.request_stop()
        default_log("Interrupted; progress saved.")


if __name__ == "__main__":
    main()
