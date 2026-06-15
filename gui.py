"""Desktop GUI for the chat replay tool.

Settings are stored in settings.json (editable here and in any text editor).
Run:  python gui.py
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
import run_export
from control import CONTROL
from settings_manager import (
    ALL_ATTACHMENT_KINDS,
    ATTACHMENT_LABELS,
    MODE_LABELS,
    MODE_TG_ONLY,
    MODE_VK_AND_TG,
    MODE_VK_ONLY,
    MODES,
    SETTINGS_FILE,
    TG_ATTACHMENT_KINDS,
    VK_ATTACHMENT_KINDS,
    apply_task,
    default_attachments_filter,
    default_settings,
    default_task,
    load_settings,
    normalize_path,
    normalize_task,
    save_settings,
    settings_summary,
    task_summary,
    validate_task,
)

try:
    import psutil
except Exception:  # noqa: BLE001
    psutil = None

POLL_MS = 300
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_BIG = ("Segoe UI", 14, "bold")
FONT_SM = ("Segoe UI", 9)
ACCENT = "#2563eb"
BG = "#f4f6f9"
LOG_BG = "#0f1419"
LOG_FG = "#e6edf3"


def human_mb(nbytes: float) -> str:
    return f"{nbytes / 1024 / 1024:.1f}"


def fmt_dur(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m:02d}м {s:02d}с"
    if m:
        return f"{m}м {s:02d}с"
    return f"{s}с"


# ---------------------------------------------------------------------------
#  Reusable rows
# ---------------------------------------------------------------------------

class PathRow(ttk.Frame):
    """Label + path entry + browse button."""

    def __init__(self, parent, label: str, *, is_dir=False, width=58):
        super().__init__(parent)
        self.is_dir = is_dir
        ttk.Label(self, text=label, width=14).pack(side="left", padx=(0, 4))
        self.var = tk.StringVar()
        ttk.Entry(self, textvariable=self.var, width=width).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(self, text="…", width=3, command=self._browse).pack(side="left")

    def _browse(self):
        if self.is_dir:
            p = filedialog.askdirectory(initialdir=self.var.get() or os.getcwd())
        else:
            p = filedialog.askopenfilename(
                initialdir=os.path.dirname(self.var.get()) if self.var.get() else os.getcwd(),
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
            )
        if p:
            self.var.set(normalize_path(p))

    def get(self) -> str:
        return normalize_path(self.var.get())

    def set(self, value: str):
        self.var.set(value or "")


class VkExportRow(ttk.Frame):
    """One VK JSON export: file path + label + remove."""

    def __init__(self, parent, on_remove, on_path_change=None):
        super().__init__(parent)
        self.on_remove = on_remove
        self.on_path_change = on_path_change

        ttk.Label(self, text="JSON:", width=8).grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        self.path_var.trace_add("write", lambda *_: self._path_changed())
        ttk.Entry(self, textvariable=self.path_var, width=50).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(self, text="…", width=3, command=self._browse).grid(row=0, column=2)
        ttk.Label(self, text="Заголовок:", width=10).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var, width=24).grid(
            row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Button(self, text="✕", width=3, command=lambda: self.on_remove(self)).grid(
            row=0, column=3, rowspan=2, padx=(8, 0))
        self.columnconfigure(1, weight=1)

    def _browse(self):
        p = filedialog.askopenfilename(
            initialdir=os.path.dirname(self.path_var.get()) if self.path_var.get() else os.getcwd(),
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if p:
            self.path_var.set(normalize_path(p))

    def _path_changed(self):
        if self.on_path_change:
            self.on_path_change()

    def get(self) -> dict:
        return {"path": normalize_path(self.path_var.get()),
                "label": self.label_var.get().strip()}

    def set(self, data: dict):
        self.path_var.set(data.get("path", ""))
        self.label_var.set(data.get("label", ""))


class TgExportRow(ttk.Frame):
    """One Telegram export: folder path + section label + remove."""

    def __init__(self, parent, on_remove, on_path_change=None):
        super().__init__(parent)
        self.on_remove = on_remove
        self.on_path_change = on_path_change

        ttk.Label(self, text="Папка:", width=8).grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        self.path_var.trace_add("write", lambda *_: self._path_changed())
        ttk.Entry(self, textvariable=self.path_var, width=50).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(self, text="…", width=3, command=self._browse).grid(row=0, column=2)
        ttk.Label(self, text="Заголовок:", width=10).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var, width=24).grid(
            row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Button(self, text="✕", width=3, command=lambda: self.on_remove(self)).grid(
            row=0, column=3, rowspan=2, padx=(8, 0))
        self.columnconfigure(1, weight=1)

    def _browse(self):
        p = filedialog.askdirectory(initialdir=self.path_var.get() or os.getcwd())
        if p:
            self.path_var.set(normalize_path(p))

    def _path_changed(self):
        if self.on_path_change:
            self.on_path_change()

    def get(self) -> dict:
        return {"path": normalize_path(self.path_var.get()),
                "label": self.label_var.get().strip()}

    def set(self, data: dict):
        self.path_var.set(data.get("path", ""))
        self.label_var.set(data.get("label", ""))


class BotRow(ttk.Frame):
    """One bot configuration: key/name, token, system/default flags."""

    def __init__(self, parent, on_remove):
        super().__init__(parent)
        self.on_remove = on_remove

        row0 = ttk.Frame(self)
        row0.pack(fill="x")
        ttk.Label(row0, text="Имя:", width=6).pack(side="left")
        self.key_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.key_var, width=14).pack(side="left", padx=4)
        ttk.Label(row0, text="Токен:", width=6).pack(side="left")
        self.token_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.token_var, width=36, show="•").pack(
            side="left", fill="x", expand=True, padx=4)
        self.is_system = tk.BooleanVar()
        ttk.Checkbutton(row0, text="Сист.", variable=self.is_system).pack(side="left", padx=2)
        self.is_default = tk.BooleanVar()
        ttk.Checkbutton(row0, text="По ум.", variable=self.is_default).pack(side="left", padx=2)
        ttk.Button(row0, text="✕", width=3, command=lambda: self.on_remove(self)).pack(
            side="left", padx=(4, 0))

        row1 = ttk.Frame(self)
        row1.pack(fill="x", pady=(2, 0))
        ttk.Label(row1, text="Отобр.:", width=6, foreground="#666").pack(side="left")
        self.display_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.display_var, width=14).pack(side="left", padx=4)
        ttk.Label(row1, text="VK ID:", width=6, foreground="#666").pack(side="left")
        self.vk_ids_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.vk_ids_var, width=16).pack(side="left", padx=4)
        ttk.Label(row1, text="TG имена:", foreground="#666").pack(side="left")
        self.tg_names_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.tg_names_var, width=24).pack(
            side="left", fill="x", expand=True, padx=4)

    def get_key(self) -> str:
        return self.key_var.get().strip()

    def get_data(self) -> dict:
        return {
            "key": self.get_key(),
            "token": self.token_var.get().strip(),
            "display_name": self.display_var.get().strip(),
            "vk_ids": [s.strip() for s in self.vk_ids_var.get().split(",") if s.strip()],
            "tg_names": [s.strip() for s in self.tg_names_var.get().split(",") if s.strip()],
            "is_system": self.is_system.get(),
            "is_default": self.is_default.get(),
        }

    def set_data(self, data: dict):
        self.key_var.set(data.get("key", ""))
        self.token_var.set(data.get("token", ""))
        self.display_var.set(data.get("display_name", ""))
        self.vk_ids_var.set(", ".join(data.get("vk_ids", [])))
        self.tg_names_var.set(", ".join(data.get("tg_names", [])))
        self.is_system.set(data.get("is_system", False))
        self.is_default.set(data.get("is_default", False))


# ---------------------------------------------------------------------------
#  Task panel (one collapsible task configuration)
# ---------------------------------------------------------------------------

class TaskPanel(ttk.LabelFrame):
    """Complete settings panel for one replay task."""

    def __init__(self, parent, task_index: int, on_remove, on_detect_senders):
        self.task_index = task_index
        self.on_remove_cb = on_remove
        self.on_detect_senders = on_detect_senders
        self.vk_rows: list[VkExportRow] = []
        self.tg_rows: list[TgExportRow] = []
        self.bot_rows: list[BotRow] = []
        self.att_vars: dict[str, tk.BooleanVar] = {}
        self._detected_vk = tk.StringVar(value="")
        self._detected_tg = tk.StringVar(value="")

        self.name_var = tk.StringVar(value=f"Задача {task_index + 1}")
        super().__init__(parent, text=f"Задача {task_index + 1}", padding=10)

        self._build()

    def _build(self):
        # Name + delete
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Название:").pack(side="left")
        self.name_var.trace_add("write", lambda *_: self.configure(
            text=self.name_var.get() or f"Задача {self.task_index + 1}"))
        ttk.Entry(top, textvariable=self.name_var, width=24).pack(side="left", padx=8)
        ttk.Button(top, text="✕ Удалить задачу", command=self._on_remove).pack(side="right")

        # Target chat
        tf = ttk.LabelFrame(self, text="Целевой чат Telegram", padding=8)
        tf.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(tf)
        row.pack(fill="x")
        ttk.Label(row, text="Chat ID:").pack(side="left")
        self.chat_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.chat_var, width=22).pack(side="left", padx=8)
        ttk.Label(row, text="(для супергруппы: -100…)", foreground="#666").pack(side="left")

        # Mode
        mf = ttk.LabelFrame(self, text="Режим отправки", padding=8)
        mf.pack(fill="x", pady=(0, 6))
        self.mode_var = tk.StringVar(value=MODE_VK_AND_TG)
        mode_row = ttk.Frame(mf)
        mode_row.pack(fill="x")
        for mode in MODES:
            ttk.Radiobutton(mode_row, text=MODE_LABELS[mode], variable=self.mode_var,
                            value=mode, command=self._on_mode_change).pack(side="left", padx=(0, 12))
        self.multichat_var = tk.BooleanVar()
        ttk.Checkbutton(mf, text="Мульти-чат (один бот, [Имя] перед сообщением)",
                        variable=self.multichat_var).pack(anchor="w", pady=(6, 0))

        # VK sources
        self.vk_frame = ttk.LabelFrame(self, text="ВКонтакте — JSON экспорт (+)", padding=8)
        self.vk_frame.pack(fill="x", pady=(0, 6))
        self.vk_list = ttk.Frame(self.vk_frame)
        self.vk_list.pack(fill="x")
        ttk.Button(self.vk_frame, text="+ Добавить VK JSON",
                   command=self._add_vk_row).pack(anchor="w", pady=(6, 0))

        # TG sources
        self.tg_frame = ttk.LabelFrame(self, text="Telegram — папки экспорта (+)", padding=8)
        self.tg_frame.pack(fill="x", pady=(0, 6))
        self.tg_list = ttk.Frame(self.tg_frame)
        self.tg_list.pack(fill="x")
        ttk.Button(self.tg_frame, text="+ Добавить папку TG",
                   command=self._add_tg_row).pack(anchor="w", pady=(6, 0))

        # Bots & senders
        bf = ttk.LabelFrame(self, text="Боты и отправители", padding=8)
        bf.pack(fill="x", pady=(0, 6))
        self.bot_list = ttk.Frame(bf)
        self.bot_list.pack(fill="x")
        btn_row = ttk.Frame(bf)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="+ Добавить бота",
                   command=self._add_bot_row).pack(side="left")
        ttk.Button(btn_row, text="🔍 Обнаружить отправителей",
                   command=self._detect_senders).pack(side="left", padx=8)
        # Detected senders display
        det = ttk.Frame(bf)
        det.pack(fill="x", pady=(4, 0))
        ttk.Label(det, textvariable=self._detected_vk, foreground="#666",
                  font=FONT_SM, wraplength=800).pack(anchor="w")
        ttk.Label(det, textvariable=self._detected_tg, foreground="#666",
                  font=FONT_SM, wraplength=800).pack(anchor="w")

        # Attachment filter
        af = ttk.LabelFrame(self, text="Вложения (что отправлять)", padding=8)
        af.pack(fill="x", pady=(0, 6))
        self.att_frame = ttk.Frame(af)
        self.att_frame.pack(fill="x")
        for kind in ALL_ATTACHMENT_KINDS:
            v = tk.BooleanVar(value=True)
            self.att_vars[kind] = v
            ttk.Checkbutton(self.att_frame, text=ATTACHMENT_LABELS.get(kind, kind),
                            variable=v).pack(side="left", padx=(0, 8))

        # Rate & behavior
        rf = ttk.LabelFrame(self, text="Скорость и поведение", padding=8)
        rf.pack(fill="x", pady=(0, 6))
        g = ttk.Frame(rf)
        g.pack(fill="x")
        ttk.Label(g, text="Пауза, с:").grid(row=0, column=0, sticky="w", pady=4)
        self.delay_var = tk.StringVar(value="1.5")
        ttk.Entry(g, textvariable=self.delay_var, width=8).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(g, text="Попыток медиа:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.send_attempts_var = tk.StringVar(value="6")
        ttk.Entry(g, textvariable=self.send_attempts_var, width=6).grid(
            row=0, column=3, sticky="w", padx=6)
        self.date_hdr = tk.BooleanVar(value=True)
        self.sect_hdr = tk.BooleanVar(value=True)
        self.placeholders = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text="Заголовки дат", variable=self.date_hdr).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(g, text="Заголовки секций", variable=self.sect_hdr).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(g, text="Заглушки для отсутствующих файлов",
                        variable=self.placeholders).grid(row=2, column=0, columnspan=4, sticky="w")

    def _on_remove(self):
        self.on_remove_cb(self)

    def _on_mode_change(self):
        """Update attachment filter visibility based on mode."""
        mode = self.mode_var.get()
        if mode == MODE_VK_ONLY:
            kinds = VK_ATTACHMENT_KINDS
        elif mode == MODE_TG_ONLY:
            kinds = TG_ATTACHMENT_KINDS
        else:
            kinds = ALL_ATTACHMENT_KINDS
        for kind, var in self.att_vars.items():
            # All attachment checkboxes remain visible; user controls them manually
            pass

    # ---- VK rows ----
    def _add_vk_row(self, data: dict | None = None):
        row = VkExportRow(self.vk_list, self._remove_vk_row,
                          on_path_change=self._detect_senders)
        row.pack(fill="x", pady=4)
        self.vk_rows.append(row)
        if data:
            row.set(data)
        else:
            row.label_var.set(f"ВК {len(self.vk_rows)}" if len(self.vk_rows) > 1 else "ВК")

    def _remove_vk_row(self, row):
        if row in self.vk_rows:
            self.vk_rows.remove(row)
            row.destroy()

    # ---- TG rows ----
    def _add_tg_row(self, data: dict | None = None):
        row = TgExportRow(self.tg_list, self._remove_tg_row,
                          on_path_change=self._detect_senders)
        row.pack(fill="x", pady=4)
        self.tg_rows.append(row)
        if data:
            row.set(data)
        else:
            n = len(self.tg_rows)
            row.label_var.set(f"Телеграм {n}" if n > 1 else "Телеграм")

    def _remove_tg_row(self, row):
        if row in self.tg_rows:
            self.tg_rows.remove(row)
            row.destroy()

    # ---- Bot rows ----
    def _add_bot_row(self, data: dict | None = None):
        row = BotRow(self.bot_list, self._remove_bot_row)
        row.pack(fill="x", pady=4)
        self.bot_rows.append(row)
        if data:
            row.set_data(data)
        else:
            n = len(self.bot_rows)
            row.key_var.set(f"bot{n}")
            if n == 1:
                row.is_default.set(True)
                row.is_system.set(True)

    def _remove_bot_row(self, row):
        if row in self.bot_rows:
            self.bot_rows.remove(row)
            row.destroy()

    # ---- Detect senders ----
    def _detect_senders(self):
        """Auto-detect sender IDs/names from source files."""
        def work():
            import vk_parser as vkp
            import tg_parser as tgp
            # VK
            vk_ids = set()
            for r in self.vk_rows:
                path = r.get()["path"]
                if path and os.path.isfile(path):
                    vk_ids.update(vkp.extract_sender_ids(path))
            # TG
            tg_names = set()
            for r in self.tg_rows:
                path = r.get()["path"]
                if path and os.path.isdir(path):
                    tg_names.update(tgp.extract_sender_names(path))
            vk_str = f"VK отправители: {', '.join(sorted(vk_ids))}" if vk_ids else ""
            tg_str = f"TG отправители: {', '.join(sorted(tg_names))}" if tg_names else ""
            self._detected_vk.set(vk_str)
            self._detected_tg.set(tg_str)

        threading.Thread(target=work, daemon=True).start()

    # ---- Serialize / deserialize ----
    def to_task(self) -> dict:
        """Convert panel state to a task dict."""
        vk_exports = [r.get() for r in self.vk_rows if r.get().get("path")]
        tg_exports = [r.get() for r in self.tg_rows if r.get().get("path")]

        bots = {}
        sender_map = {"vk": {}, "vk_default": "", "telegram": {}, "telegram_default": ""}
        display_names = {}
        system_bot = ""
        multichat_bot = ""

        for br in self.bot_rows:
            d = br.get_data()
            key = d["key"]
            if not key:
                continue
            bots[key] = d["token"]
            display_names[key] = d["display_name"] or key
            for vid in d["vk_ids"]:
                sender_map["vk"][vid] = key
            for tname in d["tg_names"]:
                sender_map["telegram"][tname.lower()] = key
            if d["is_default"]:
                sender_map["vk_default"] = key
                sender_map["telegram_default"] = key
                multichat_bot = key
            if d["is_system"]:
                system_bot = key

        return {
            "name": self.name_var.get().strip() or f"Задача {self.task_index + 1}",
            "mode": self.mode_var.get(),
            "multichat": self.multichat_var.get(),
            "multichat_bot": multichat_bot,
            "target": {"chat_id": self.chat_var.get().strip()},
            "sources": {
                "vk_exports": vk_exports,
                "vk_media_mirrors": [],  # keep from existing settings
                "telegram_exports": tg_exports,
            },
            "bots": bots,
            "sender_map": sender_map,
            "display_names": display_names,
            "system_bot": system_bot,
            "attachments_filter": {k: v.get() for k, v in self.att_vars.items()},
            "rate": {
                "min_interval_seconds": self.delay_var.get().strip(),
            },
            "retry": {
                "send_media_attempts": self.send_attempts_var.get().strip(),
            },
            "behavior": {
                "send_date_headers": self.date_hdr.get(),
                "send_section_headers": self.sect_hdr.get(),
                "placeholders_for_missing": self.placeholders.get(),
            },
        }

    def from_task(self, t: dict):
        """Populate panel from a task dict."""
        t = normalize_task(t)
        self.name_var.set(t.get("name", f"Задача {self.task_index + 1}"))
        self.configure(text=self.name_var.get())
        self.mode_var.set(t.get("mode", MODE_VK_AND_TG))
        self.multichat_var.set(t.get("multichat", False))
        self.chat_var.set(str(t["target"]["chat_id"]))

        # VK exports
        for r in list(self.vk_rows):
            self._remove_vk_row(r)
        for ex in t["sources"].get("vk_exports") or []:
            self._add_vk_row(ex)

        # TG exports
        for r in list(self.tg_rows):
            self._remove_tg_row(r)
        for ex in t["sources"].get("telegram_exports") or []:
            self._add_tg_row(ex)

        # Bots
        for r in list(self.bot_rows):
            self._remove_bot_row(r)
        sm = t.get("sender_map", {})
        dn = t.get("display_names", {})
        vk_map_inv: dict[str, list[str]] = {}
        for vid, bkey in (sm.get("vk") or {}).items():
            vk_map_inv.setdefault(bkey, []).append(str(vid))
        tg_map_inv: dict[str, list[str]] = {}
        for tname, bkey in (sm.get("telegram") or {}).items():
            tg_map_inv.setdefault(bkey, []).append(tname)

        for key, token in (t.get("bots") or {}).items():
            self._add_bot_row({
                "key": key,
                "token": token,
                "display_name": dn.get(key, ""),
                "vk_ids": vk_map_inv.get(key, []),
                "tg_names": tg_map_inv.get(key, []),
                "is_system": key == t.get("system_bot", ""),
                "is_default": key == sm.get("vk_default", "") or key == sm.get("telegram_default", ""),
            })

        # Attachments
        af = t.get("attachments_filter") or {}
        for k, v in self.att_vars.items():
            v.set(af.get(k, True))

        # Rate & behavior
        self.delay_var.set(str(t["rate"].get("min_interval_seconds", 1.5)))
        self.send_attempts_var.set(str(t["retry"].get("send_media_attempts", 6)))
        beh = t.get("behavior", {})
        self.date_hdr.set(beh.get("send_date_headers", True))
        self.sect_hdr.set(beh.get("send_section_headers", True))
        self.placeholders.set(beh.get("placeholders_for_missing", True))


# ---------------------------------------------------------------------------
#  Main application
# ---------------------------------------------------------------------------

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.worker: threading.Thread | None = None
        self.verify_proc: subprocess.Popen | None = None
        self.logq: queue.Queue[str] = queue.Queue()
        self.proc = psutil.Process(os.getpid()) if psutil else None
        if self.proc:
            try:
                self.proc.cpu_percent(None)
            except Exception:
                pass
        self._cache_ts = 0.0
        self._cache_str = "—"
        self.err_win: tk.Toplevel | None = None
        self.err_tree: ttk.Treeview | None = None
        self.err_shown = 0
        self.task_panels: list[TaskPanel] = []
        self.active_task_idx = 0

        root.title("Replay — VK / Telegram → Telegram")
        root.geometry("1020x860")
        root.minsize(780, 560)
        root.configure(bg=BG)

        # Set window icon
        ico = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.isfile(ico):
            try:
                root.iconbitmap(ico)
            except Exception:
                pass

        self._style()
        self._build_header()
        self._build_notebook()
        self._load_from_file()
        self._poll()

    # ---- styling ----------------------------------------------------
    def _style(self):
        s = ttk.Style()
        try:
            s.theme_use("vista")
        except tk.TclError:
            pass
        s.configure("TNotebook", background=BG)
        s.configure("TNotebook.Tab", padding=[14, 6], font=FONT)
        s.configure("TFrame", background=BG)
        s.configure("TLabelframe", background=BG)
        s.configure("TLabelframe.Label", font=FONT_BOLD, background=BG)
        s.configure("TLabel", background=BG, font=FONT)
        s.configure("Header.TLabel", font=FONT_TITLE, background=BG, foreground=ACCENT)
        s.configure("Sub.TLabel", font=FONT, background=BG, foreground="#555")
        s.configure("Accent.TButton", font=FONT_BOLD)

    def _build_header(self):
        bar = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Replay", style="Header.TLabel").pack(side="left")
        self.var_summary = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_summary, style="Sub.TLabel").pack(
            side="left", padx=(12, 0))

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tab_run = ttk.Frame(self.nb, padding=8)
        self.tab_cfg = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_run, text="  ▶ Запуск  ")
        self.nb.add(self.tab_cfg, text="  ⚙ Настройки  ")

        self._build_run_tab()
        self._build_settings_tab()

    # ---- Run tab ----------------------------------------------------
    def _build_run_tab(self):
        # Task selector
        sel = ttk.Frame(self.tab_run)
        sel.pack(fill="x", pady=(0, 6))
        ttk.Label(sel, text="Задача:").pack(side="left")
        self.task_combo = ttk.Combobox(sel, state="readonly", width=30)
        self.task_combo.pack(side="left", padx=8)
        self.task_combo.bind("<<ComboboxSelected>>", self._on_task_selected)

        # Controls
        ctrl = ttk.Frame(self.tab_run)
        ctrl.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(ctrl, text="▶ Старт", style="Accent.TButton",
                                    command=self.on_start)
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_pause = ttk.Button(ctrl, text="⏸ Пауза", command=self.on_pause, state="disabled")
        self.btn_skip = ttk.Button(ctrl, text="⏭ Пропустить", command=self.on_skip, state="disabled")
        self.btn_stop = ttk.Button(ctrl, text="⏹ Стоп", command=self.on_stop, state="disabled")
        for b in (self.btn_pause, self.btn_skip, self.btn_stop):
            b.pack(side="left", padx=4)
        ttk.Separator(ctrl, orient="vertical").pack(side="left", fill="y", padx=10, pady=2)
        ttk.Button(ctrl, text="🧪 Тест", command=self.on_verify).pack(side="left", padx=4)
        ttk.Button(ctrl, text="🚨 Ошибки", command=self.on_errors).pack(side="left", padx=4)
        ttk.Button(ctrl, text="📄 Лог", command=self.on_open_log).pack(side="left", padx=4)
        self.reset_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Начать заново", variable=self.reset_var).pack(
            side="right", padx=4)

        # Progress
        pf = ttk.LabelFrame(self.tab_run, text="Прогресс", padding=8)
        pf.pack(fill="x", pady=4)
        self.pbar = ttk.Progressbar(pf, mode="determinate", maximum=100)
        self.pbar.pack(fill="x", pady=(0, 6))
        self.lbl_prog = ttk.Label(pf, text="0 / 0 (0%)", font=FONT_BIG)
        self.lbl_prog.pack(anchor="w")
        row = ttk.Frame(pf)
        row.pack(fill="x", pady=6)
        self.var_phase = tk.StringVar(value="Фаза: —")
        self.var_elapsed = tk.StringVar(value="Прошло: —")
        self.var_eta = tk.StringVar(value="Осталось: —")
        self.var_rate = tk.StringVar(value="Скорость: —")
        for i, v in enumerate((self.var_phase, self.var_elapsed, self.var_eta, self.var_rate)):
            ttk.Label(row, textvariable=v).grid(row=0, column=i, sticky="w", padx=(0, 16))
        self.var_current = tk.StringVar(value="Текущее: —")
        ttk.Label(pf, textvariable=self.var_current, foreground="#444").pack(anchor="w")
        self.var_file = tk.StringVar(value="Файл: —")
        ttk.Label(pf, textvariable=self.var_file, foreground="#777").pack(anchor="w", pady=(0, 4))
        sub = ttk.Frame(pf)
        sub.pack(fill="x")
        ttk.Label(sub, text="ВК:", width=4).grid(row=0, column=0, sticky="w")
        self.vk_bar = ttk.Progressbar(sub, maximum=100)
        self.vk_bar.grid(row=0, column=1, sticky="ew", padx=6)
        self.var_vk = tk.StringVar(value="0 / 0")
        ttk.Label(sub, textvariable=self.var_vk, width=14).grid(row=0, column=2)
        ttk.Label(sub, text="ТГ:", width=4).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.tg_bar = ttk.Progressbar(sub, maximum=100)
        self.tg_bar.grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))
        self.var_tg = tk.StringVar(value="0 / 0")
        ttk.Label(sub, textvariable=self.var_tg, width=14).grid(row=1, column=2, pady=(4, 0))
        sub.columnconfigure(1, weight=1)

        # Stats + resources in one row
        mid = ttk.Panedwindow(self.tab_run, orient="vertical")
        mid.pack(fill="both", expand=True, pady=4)

        stats_f = ttk.LabelFrame(mid, text="Статистика", padding=6)
        mid.add(stats_f, weight=1)
        self.stat_vars: dict[str, tk.StringVar] = {}
        items = [
            ("text", "Текст"), ("photo", "Фото"), ("sticker", "Стикеры"),
            ("voice", "Голос"), ("video", "Видео"), ("document", "Файлы"),
            ("header", "Заголовки"), ("placeholders", "Заглушки"),
            ("skipped", "Пропуск"), ("errors", "Ошибки"), ("retries", "Повторы"),
        ]
        grid = ttk.Frame(stats_f)
        grid.pack(fill="x")
        for idx, (key, label) in enumerate(items):
            r, c = divmod(idx, 6)
            cell = ttk.Frame(grid)
            cell.grid(row=r, column=c, sticky="w", padx=8, pady=4)
            v = tk.StringVar(value="0")
            self.stat_vars[key] = v
            ttk.Label(cell, textvariable=v, font=FONT_BIG).pack(anchor="w")
            ttk.Label(cell, text=label, foreground="#666").pack(anchor="w")
        self.var_lasterr = tk.StringVar(value="")
        ttk.Label(stats_f, textvariable=self.var_lasterr, foreground="#b00000").pack(
            anchor="w", pady=(4, 0))

        res_f = ttk.LabelFrame(mid, text="Ресурсы", padding=6)
        mid.add(res_f, weight=0)
        self.res_vars: dict[str, tk.StringVar] = {}
        res_items = [
            ("ram", "RAM"), ("cpu", "CPU"), ("threads", "Потоки"),
            ("downloads", "Загрузок"), ("flood", "429"),
        ]
        rg = ttk.Frame(res_f)
        rg.pack(fill="x")
        for idx, (key, label) in enumerate(res_items):
            cell = ttk.Frame(rg)
            cell.grid(row=0, column=idx, sticky="w", padx=10, pady=2)
            v = tk.StringVar(value="—")
            self.res_vars[key] = v
            ttk.Label(cell, textvariable=v, font=FONT_BOLD).pack(anchor="w")
            ttk.Label(cell, text=label, foreground="#666").pack(anchor="w")

        # Log
        lf = ttk.LabelFrame(self.tab_run, text="Журнал", padding=4)
        lf.pack(fill="both", expand=True, pady=(4, 0))
        self.txt = tk.Text(lf, height=8, wrap="word", state="disabled",
                           font=("Consolas", 9), background=LOG_BG, foreground=LOG_FG,
                           insertbackground=LOG_FG, relief="flat", padx=8, pady=6)
        sb = ttk.Scrollbar(lf, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ---- Settings tab -----------------------------------------------
    def _build_settings_tab(self):
        outer = ttk.Frame(self.tab_cfg)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, background=BG)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.cfg_body = ttk.Frame(canvas)
        self.cfg_win = canvas.create_window((0, 0), window=self.cfg_body, anchor="nw")
        self.cfg_body.bind("<Configure>",
                           lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(self.cfg_win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.cfg_canvas = canvas

        # Task panels container
        self.tasks_frame = ttk.Frame(self.cfg_body)
        self.tasks_frame.pack(fill="x", pady=(0, 8))

        # Add task + action buttons
        bf = ttk.Frame(self.cfg_body)
        bf.pack(fill="x", pady=8)
        ttk.Button(bf, text="+ Добавить задачу",
                   command=self._add_task_panel).pack(side="left", padx=(0, 16))
        ttk.Separator(bf, orient="vertical").pack(side="left", fill="y", padx=4, pady=2)
        ttk.Button(bf, text="💾 Сохранить настройки", style="Accent.TButton",
                   command=self.on_save_settings).pack(side="left", padx=8)
        ttk.Button(bf, text="↻ Перезагрузить из файла",
                   command=self._load_from_file).pack(side="left", padx=4)
        ttk.Button(bf, text="📂 Открыть settings.json",
                   command=self.on_open_settings).pack(side="left", padx=4)
        ttk.Button(bf, text="🔍 Проверить пути",
                   command=self.on_validate).pack(side="left", padx=4)

    # ---- Task panel management ----
    def _add_task_panel(self, task_data: dict | None = None) -> TaskPanel:
        idx = len(self.task_panels)
        panel = TaskPanel(self.tasks_frame, idx, self._remove_task_panel,
                          self._on_detect_senders)
        panel.pack(fill="x", pady=(0, 12))
        self.task_panels.append(panel)
        if task_data:
            panel.from_task(task_data)
        self._update_task_combo()
        return panel

    def _remove_task_panel(self, panel: TaskPanel):
        if len(self.task_panels) <= 1:
            messagebox.showinfo("Задачи", "Нельзя удалить единственную задачу.")
            return
        if panel in self.task_panels:
            self.task_panels.remove(panel)
            panel.destroy()
            # Reindex
            for i, p in enumerate(self.task_panels):
                p.task_index = i
            self._update_task_combo()

    def _on_detect_senders(self, panel: TaskPanel = None):
        pass  # Detection happens inside TaskPanel

    def _update_task_combo(self):
        names = [p.name_var.get() or f"Задача {i + 1}"
                 for i, p in enumerate(self.task_panels)]
        self.task_combo["values"] = names
        if names:
            idx = min(self.active_task_idx, len(names) - 1)
            self.task_combo.current(idx)
            self.active_task_idx = idx

    def _on_task_selected(self, event=None):
        self.active_task_idx = self.task_combo.current()

    # ---- settings I/O -----------------------------------------------
    def _settings_from_ui(self) -> dict:
        """Build a full settings dict from the UI state."""
        # Get existing settings to preserve fields not shown in UI (e.g., vk_media_mirrors)
        try:
            existing = load_settings()
        except Exception:
            existing = default_settings()

        tasks = []
        for i, panel in enumerate(self.task_panels):
            t = panel.to_task()
            # Preserve vk_media_mirrors from existing
            if i < len(existing.get("tasks", [])):
                old_src = existing["tasks"][i].get("sources", {})
                t["sources"]["vk_media_mirrors"] = old_src.get("vk_media_mirrors", [])
                # Preserve rate/retry fields not shown in UI
                old_rate = existing["tasks"][i].get("rate", {})
                for k in ("jitter_seconds", "error_backoff_seconds",
                          "http_connect_timeout", "http_read_timeout"):
                    if k in old_rate:
                        t["rate"][k] = old_rate[k]
                old_retry = existing["tasks"][i].get("retry", {})
                for k in ("media_download_attempts", "media_retry_backoff_seconds"):
                    if k in old_retry:
                        t["retry"][k] = old_retry[k]
            tasks.append(t)
        return {"tasks": tasks}

    def _settings_to_ui(self, s: dict):
        """Populate UI from settings dict."""
        # Clear existing panels
        for p in list(self.task_panels):
            p.destroy()
        self.task_panels.clear()

        tasks = s.get("tasks", [])
        if not tasks:
            tasks = [default_task()]
        for t in tasks:
            self._add_task_panel(t)

        self._update_task_combo()
        self.var_summary.set(settings_summary(s))

    def _load_from_file(self):
        try:
            s = load_settings()
            self._settings_to_ui(s)
            # Apply first task
            if s["tasks"]:
                apply_task(s["tasks"][0], 0)
            self.log("Настройки загружены из settings.json")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Ошибка", f"Не удалось загрузить settings.json:\n{e}")

    def on_save_settings(self):
        try:
            s = self._settings_from_ui()
            # Validate all tasks
            all_errs = []
            for i, t in enumerate(s.get("tasks", [])):
                errs = validate_task(t)
                if errs:
                    name = t.get("name", f"Задача {i + 1}")
                    all_errs.extend(f"[{name}] {e}" for e in errs)
            if all_errs:
                messagebox.showwarning(
                    "Проверка",
                    "Сохранено, но есть замечания:\n\n" + "\n".join(f"• {e}" for e in all_errs))
            path = save_settings(s)
            # Re-apply active task
            tasks = s.get("tasks", [])
            if self.active_task_idx < len(tasks):
                apply_task(tasks[self.active_task_idx], self.active_task_idx)
            self.var_summary.set(settings_summary(s))
            self.log(f"Настройки сохранены: {path}")
            messagebox.showinfo("Сохранено", f"Настройки записаны в\n{path}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(e))

    def on_validate(self):
        s = self._settings_from_ui()
        all_errs = []
        for i, t in enumerate(s.get("tasks", [])):
            errs = validate_task(t)
            name = t.get("name", f"Задача {i + 1}")
            all_errs.extend(f"[{name}] {e}" for e in errs)
        if all_errs:
            messagebox.showwarning("Проверка", "\n".join(f"• {e}" for e in all_errs))
        else:
            messagebox.showinfo("Проверка", "Все пути и параметры в порядке ✓")

    def on_open_settings(self):
        path = SETTINGS_FILE
        if not os.path.isfile(path):
            save_settings(default_settings(), path)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo("Файл", path)

    # ---- logging ----------------------------------------------------
    def log(self, msg: str):
        self.logq.put(msg)

    def _drain_log(self):
        appended = False
        while True:
            try:
                line = self.logq.get_nowait()
            except queue.Empty:
                break
            self.txt.configure(state="normal")
            self.txt.insert("end", line + "\n")
            appended = True
        if appended:
            self.txt.see("end")
            self.txt.configure(state="disabled")

    # ---- run actions ------------------------------------------------
    def on_start(self):
        if self.worker and self.worker.is_alive():
            return
        s = self._settings_from_ui()
        tasks = s.get("tasks", [])
        idx = self.active_task_idx
        if idx >= len(tasks):
            messagebox.showerror("Ошибка", "Не выбрана задача.")
            return
        task = tasks[idx]
        errs = validate_task(task)
        if errs:
            if not messagebox.askyesno(
                    "Предупреждение",
                    "Есть проблемы с настройками:\n\n"
                    + "\n".join(f"• {e}" for e in errs)
                    + "\n\nВсё равно запустить?"):
                return
        try:
            save_settings(s)
            apply_task(task, idx)
            self.var_summary.set(settings_summary(s))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(e))
            return

        reset = self.reset_var.get()
        self._set_running(True)
        name = task.get("name", f"Задача {idx + 1}")
        self.log(f"=== Запуск: {name} ===")
        self.log(task_summary(task))

        def work():
            try:
                run_export.run(reset=reset, log=self.log)
            except Exception as e:  # noqa: BLE001
                self.log(f"!!! Критическая ошибка: {e}")
            finally:
                self.root.after(0, lambda: self._set_running(False))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def on_pause(self):
        if CONTROL.is_paused():
            CONTROL.resume()
            self.btn_pause.config(text="⏸ Пауза")
            self.log("Продолжено.")
        else:
            CONTROL.pause()
            self.btn_pause.config(text="▶ Продолжить")
            self.log("Пауза.")

    def on_skip(self):
        CONTROL.request_skip()
        self.log("Запрошен пропуск…")

    def on_stop(self):
        if messagebox.askyesno("Стоп", "Остановить? Прогресс сохранится."):
            CONTROL.request_stop()
            self.log("Остановка…")

    def on_verify(self):
        if self.verify_proc and self.verify_proc.poll() is None:
            return
        # Apply active task first
        s = self._settings_from_ui()
        tasks = s.get("tasks", [])
        idx = self.active_task_idx
        if idx < len(tasks):
            apply_task(tasks[idx], idx)
        self.log("=== Тест вложений ===")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")

        def work():
            try:
                self.verify_proc = subprocess.Popen(
                    [sys.executable, os.path.join(os.path.dirname(__file__), "verify.py")],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env)
                for line in self.verify_proc.stdout:
                    self.log(line.rstrip())
            except Exception as e:  # noqa: BLE001
                self.log(f"verify error: {e}")

        threading.Thread(target=work, daemon=True).start()

    def on_open_log(self):
        try:
            os.startfile(config.LOG_FILE)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo("Лог", config.LOG_FILE)

    # ---- error window -----------------------------------------------
    def on_errors(self):
        if self.err_win is not None and tk.Toplevel.winfo_exists(self.err_win):
            self.err_win.deiconify()
            self.err_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("Ошибки и события")
        win.geometry("760x420")
        self.err_win = win
        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        self.err_count_var = tk.StringVar(value="0")
        ttk.Label(top, textvariable=self.err_count_var, font=FONT_BOLD).pack(side="left")
        ttk.Button(top, text="Очистить", command=self._clear_error_window).pack(side="right")
        cols = ("time", "type", "msg")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c, w in (("time", 160), ("type", 80), ("msg", 480)):
            tree.heading(c, text={"time": "Время", "type": "Тип", "msg": "Сообщение"}[c])
            tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(win, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        for tag, color in (("429", "#b06a00"), ("СЕТЬ", "#0050b0"), ("НЕТ СЕТИ", "#888800"),
                           ("СЕРВЕР", "#7a00b0"), ("ОШИБКА", "#b00000"), ("ОТКАЗ", "#b00000")):
            tree.tag_configure(tag, foreground=color)
        self.err_tree = tree
        self.err_shown = 0
        self._refresh_error_window()

    def _clear_error_window(self):
        if self.err_tree:
            for iid in self.err_tree.get_children():
                self.err_tree.delete(iid)
        self.err_shown = 0

    def _refresh_error_window(self):
        if self.err_win is None or not tk.Toplevel.winfo_exists(self.err_win):
            self.err_win = None
            self.err_tree = None
            return
        evs = CONTROL.stats.events_snapshot()
        if len(evs) < self.err_shown:
            self._clear_error_window()
        for ev in evs[self.err_shown:]:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev["ts"]))
            tree = self.err_tree
            tree.insert("", 0, values=(ts, ev["level"], ev["msg"]), tags=(ev["level"],))
        self.err_shown = len(evs)
        self.err_count_var.set(f"Событий: {len(evs)}")

    def _set_running(self, running: bool):
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_pause.config(state="normal" if running else "disabled")
        self.btn_skip.config(state="normal" if running else "disabled")
        self.btn_stop.config(state="normal" if running else "disabled")
        # Don't lock the settings tab — allow editing other tasks while running
        self.task_combo.config(state="disabled" if running else "readonly")
        if not running:
            self.btn_pause.config(text="⏸ Пауза")

    def _poll(self):
        self._drain_log()
        s = CONTROL.stats.snapshot()
        total, idx = s["total"], s["index"]
        pct = (idx / total * 100) if total else 0
        self.pbar.config(maximum=max(1, total), value=idx)
        self.lbl_prog.config(text=f"{idx:,} / {total:,} ({pct:.1f}%)".replace(",", " "))
        self.var_phase.set(f"Фаза: {s['phase']}")
        self.var_elapsed.set(f"Прошло: {fmt_dur(s['elapsed'])}")
        self.var_eta.set(f"Осталось: {fmt_dur(s['eta'])}")
        self.var_rate.set(f"Скорость: {s['rate'] * 60:.0f}/мин")
        self.var_current.set(f"Текущее: {s['current']}")
        cf = s.get("current_file") or "—"
        self.var_file.set(f"Файл: {cf}  ({s.get('current_kind', '')})")
        vt, vd = s.get("vk_total", 0), s.get("vk_done", 0)
        tt, td = s.get("tg_total", 0), s.get("tg_done", 0)
        self.vk_bar.config(maximum=max(1, vt), value=vd)
        self.tg_bar.config(maximum=max(1, tt), value=td)
        self.var_vk.set(f"{vd:,} / {vt:,}".replace(",", " "))
        self.var_tg.set(f"{td:,} / {tt:,}".replace(",", " "))
        if self.proc:
            try:
                self.res_vars["ram"].set(f"{self.proc.memory_info().rss / 1024 / 1024:.0f} МБ")
                self.res_vars["cpu"].set(f"{self.proc.cpu_percent(None):.0f}%")
                self.res_vars["threads"].set(str(self.proc.num_threads()))
            except Exception:
                pass
        self.res_vars["downloads"].set(str(s["downloads"]))
        self.res_vars["flood"].set(str(s["flood_waits"]))
        counts = s["counts"]
        for key, var in self.stat_vars.items():
            if key in counts:
                var.set(f"{counts[key]:,}".replace(",", " "))
            elif key in ("placeholders", "skipped", "errors", "retries"):
                var.set(f"{s[key]:,}".replace(",", " "))
        self.var_lasterr.set(("⚠ " + s["last_error"]) if s["last_error"] else "")
        if self.err_win:
            self._refresh_error_window()
        self.root.after(POLL_MS, self._poll)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
