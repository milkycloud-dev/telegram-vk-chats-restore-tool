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
from i18n import t, set_lang, get_lang
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
    """Execute the human mb operation."""
    return f"{nbytes / 1024 / 1024:.1f}"


def fmt_dur(seconds: float) -> str:
    """Execute the fmt dur operation."""
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
        """Initialize the instance."""
        super().__init__(parent)
        self.is_dir = is_dir
        ttk.Label(self, text=label, width=14).pack(side="left", padx=(0, 4))
        self.var = tk.StringVar()
        ttk.Entry(self, textvariable=self.var, width=width).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(self, text="…", width=3, command=self._browse).pack(side="left")

    def _browse(self):
        """Execute the browse operation."""
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
        """Execute the get operation."""
        return normalize_path(self.var.get())

    def set(self, value: str):
        """Execute the set operation."""
        self.var.set(value or "")


class VkExportRow(ttk.Frame):
    """One VK JSON export: file path + label + remove."""

    def __init__(self, parent, on_remove, on_path_change=None):
        """Initialize the instance."""
        super().__init__(parent)
        self.on_remove = on_remove
        self.on_path_change = on_path_change

        ttk.Label(self, text="JSON:", width=8).grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        self.path_var.trace_add("write", lambda *_: self._path_changed())
        ttk.Entry(self, textvariable=self.path_var, width=50).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(self, text="…", width=3, command=self._browse).grid(row=0, column=2)
        ttk.Label(self, text=t("gui.title_label"), width=10).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var, width=24).grid(
            row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Button(self, text="✕", width=3, command=lambda: self.on_remove(self)).grid(
            row=0, column=3, rowspan=2, padx=(8, 0))
        self.columnconfigure(1, weight=1)

    def _browse(self):
        """Execute the browse operation."""
        p = filedialog.askopenfilename(
            initialdir=os.path.dirname(self.path_var.get()) if self.path_var.get() else os.getcwd(),
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if p:
            self.path_var.set(normalize_path(p))

    def _path_changed(self):
        """Execute the path changed operation."""
        if self.on_path_change:
            self.on_path_change()

    def get(self) -> dict:
        """Execute the get operation."""
        return {"path": normalize_path(self.path_var.get()),
                "label": self.label_var.get().strip()}

    def set(self, data: dict):
        """Execute the set operation."""
        self.path_var.set(data.get("path", ""))
        self.label_var.set(data.get("label", ""))


class TgExportRow(ttk.Frame):
    """One Telegram export: folder path + section label + remove."""

    def __init__(self, parent, on_remove, on_path_change=None):
        """Initialize the instance."""
        super().__init__(parent)
        self.on_remove = on_remove
        self.on_path_change = on_path_change

        ttk.Label(self, text=t("gui.folder_label"), width=8).grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar()
        self.path_var.trace_add("write", lambda *_: self._path_changed())
        ttk.Entry(self, textvariable=self.path_var, width=50).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(self, text="…", width=3, command=self._browse).grid(row=0, column=2)
        ttk.Label(self, text=t("gui.title_label"), width=10).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.label_var, width=24).grid(
            row=1, column=1, sticky="w", padx=4, pady=(4, 0))
        ttk.Button(self, text="✕", width=3, command=lambda: self.on_remove(self)).grid(
            row=0, column=3, rowspan=2, padx=(8, 0))
        self.columnconfigure(1, weight=1)

    def _browse(self):
        """Execute the browse operation."""
        p = filedialog.askdirectory(initialdir=self.path_var.get() or os.getcwd())
        if p:
            self.path_var.set(normalize_path(p))

    def _path_changed(self):
        """Execute the path changed operation."""
        if self.on_path_change:
            self.on_path_change()

    def get(self) -> dict:
        """Execute the get operation."""
        return {"path": normalize_path(self.path_var.get()),
                "label": self.label_var.get().strip()}

    def set(self, data: dict):
        """Execute the set operation."""
        self.path_var.set(data.get("path", ""))
        self.label_var.set(data.get("label", ""))


class BotRow(ttk.Frame):
    """One bot configuration: key/name, token, system/default flags."""

    def __init__(self, parent, on_remove):
        """Initialize the instance."""
        super().__init__(parent)
        self.on_remove = on_remove

        row0 = ttk.Frame(self)
        row0.pack(fill="x")
        ttk.Label(row0, text=t("gui.name_label"), width=6).pack(side="left")
        self.key_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.key_var, width=14).pack(side="left", padx=4)
        ttk.Label(row0, text=t("gui.token_label"), width=6).pack(side="left")
        self.token_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.token_var, width=36, show="•").pack(
            side="left", fill="x", expand=True, padx=4)
        self.is_system = tk.BooleanVar()
        ttk.Checkbutton(row0, text=t("gui.system_bot_flag"), variable=self.is_system).pack(side="left", padx=2)
        self.is_default = tk.BooleanVar()
        ttk.Checkbutton(row0, text=t("gui.default_bot_flag"), variable=self.is_default).pack(side="left", padx=2)
        ttk.Button(row0, text="✕", width=3, command=lambda: self.on_remove(self)).pack(
            side="left", padx=(4, 0))

        row1 = ttk.Frame(self)
        row1.pack(fill="x", pady=(2, 0))
        ttk.Label(row1, text=t("gui.display_name_label"), width=6, foreground="#666").pack(side="left")
        self.display_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.display_var, width=14).pack(side="left", padx=4)
        ttk.Label(row1, text="VK ID:", width=6, foreground="#666").pack(side="left")
        self.vk_ids_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.vk_ids_var, width=16).pack(side="left", padx=4)
        ttk.Label(row1, text=t("gui.tg_names_label"), foreground="#666").pack(side="left")
        self.tg_names_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.tg_names_var, width=24).pack(
            side="left", fill="x", expand=True, padx=4)

    def get_key(self) -> str:
        """Retrieve the key."""
        return self.key_var.get().strip()

    def get_data(self) -> dict:
        """Retrieve the data."""
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
        """Configure the data."""
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
        """Initialize the instance."""
        self.task_index = task_index
        self.on_remove_cb = on_remove
        self.on_detect_senders = on_detect_senders
        self.vk_rows: list[VkExportRow] = []
        self.tg_rows: list[TgExportRow] = []
        self.bot_rows: list[BotRow] = []
        self.att_vars: dict[str, tk.BooleanVar] = {}
        self._detected_vk = tk.StringVar(value="")
        self._detected_tg = tk.StringVar(value="")

        self.name_var = tk.StringVar(value=t("gui.task_default_name", num=task_index + 1))
        super().__init__(parent, text=t("gui.task_default_name", num=task_index + 1), padding=10)

        self._build()

    def _build(self):
        # Name + delete
        """Execute the build operation."""
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=t("gui.task_name_label")).pack(side="left")
        self.name_var.trace_add("write", lambda *_: self.configure(
            text=self.name_var.get() or t("gui.task_default_name", num=self.task_index + 1)))
        ttk.Entry(top, textvariable=self.name_var, width=24).pack(side="left", padx=8)
        ttk.Button(top, text=t("gui.delete_task_btn"), command=self._on_remove).pack(side="right")

        # Target chat
        tf = ttk.LabelFrame(self, text=t("gui.target_chat_frame"), padding=8)
        tf.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(tf)
        row.pack(fill="x")
        ttk.Label(row, text="Chat ID:").pack(side="left")
        self.chat_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.chat_var, width=22).pack(side="left", padx=8)
        ttk.Label(row, text=t("gui.supergroup_hint"), foreground="#666").pack(side="left")

        # Mode
        mf = ttk.LabelFrame(self, text=t("gui.mode_frame"), padding=8)
        mf.pack(fill="x", pady=(0, 6))
        self.mode_var = tk.StringVar(value=MODE_VK_AND_TG)
        mode_row = ttk.Frame(mf)
        mode_row.pack(fill="x")
        for mode in MODES:
            ttk.Radiobutton(mode_row, text=t(f"mode.{mode}"), variable=self.mode_var,
                            value=mode, command=self._on_mode_change).pack(side="left", padx=(0, 12))
        self.multichat_var = tk.BooleanVar()
        ttk.Checkbutton(mf, text=t("gui.multichat_cb"),
                        variable=self.multichat_var).pack(anchor="w", pady=(6, 0))

        # VK sources
        self.vk_frame = ttk.LabelFrame(self, text=t("gui.vk_frame"), padding=8)
        self.vk_frame.pack(fill="x", pady=(0, 6))
        self.vk_list = ttk.Frame(self.vk_frame)
        self.vk_list.pack(fill="x")
        ttk.Button(self.vk_frame, text=t("gui.add_vk_btn"),
                   command=self._add_vk_row).pack(anchor="w", pady=(6, 0))

        # TG sources
        self.tg_frame = ttk.LabelFrame(self, text=t("gui.tg_frame"), padding=8)
        self.tg_frame.pack(fill="x", pady=(0, 6))
        self.tg_list = ttk.Frame(self.tg_frame)
        self.tg_list.pack(fill="x")
        ttk.Button(self.tg_frame, text=t("gui.add_tg_btn"),
                   command=self._add_tg_row).pack(anchor="w", pady=(6, 0))

        # Bots & senders
        bf = ttk.LabelFrame(self, text=t("gui.bots_frame"), padding=8)
        bf.pack(fill="x", pady=(0, 6))
        self.bot_list = ttk.Frame(bf)
        self.bot_list.pack(fill="x")
        btn_row = ttk.Frame(bf)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text=t("gui.add_bot_btn"),
                   command=self._add_bot_row).pack(side="left")
        ttk.Button(btn_row, text=t("gui.detect_senders_btn"),
                   command=self._detect_senders).pack(side="left", padx=8)
        # Detected senders display
        det = ttk.Frame(bf)
        det.pack(fill="x", pady=(4, 0))
        ttk.Label(det, textvariable=self._detected_vk, foreground="#666",
                  font=FONT_SM, wraplength=800).pack(anchor="w")
        ttk.Label(det, textvariable=self._detected_tg, foreground="#666",
                  font=FONT_SM, wraplength=800).pack(anchor="w")

        # Attachment filter
        af = ttk.LabelFrame(self, text=t("gui.attachments_frame"), padding=8)
        af.pack(fill="x", pady=(0, 6))
        self.att_frame = ttk.Frame(af)
        self.att_frame.pack(fill="x")
        for kind in ALL_ATTACHMENT_KINDS:
            v = tk.BooleanVar(value=True)
            self.att_vars[kind] = v
            ttk.Checkbutton(self.att_frame, text=t(f"att.{kind}"),
                            variable=v).pack(side="left", padx=(0, 8))

        # Rate & behavior
        rf = ttk.LabelFrame(self, text=t("gui.behavior_frame"), padding=8)
        rf.pack(fill="x", pady=(0, 6))
        g = ttk.Frame(rf)
        g.pack(fill="x")
        ttk.Label(g, text=t("gui.delay_label")).grid(row=0, column=0, sticky="w", pady=4)
        self.delay_var = tk.StringVar(value="1.5")
        ttk.Entry(g, textvariable=self.delay_var, width=8).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(g, text=t("gui.retries_label")).grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.send_attempts_var = tk.StringVar(value="6")
        ttk.Entry(g, textvariable=self.send_attempts_var, width=6).grid(
            row=0, column=3, sticky="w", padx=6)
        self.date_hdr = tk.BooleanVar(value=True)
        self.sect_hdr = tk.BooleanVar(value=True)
        self.placeholders = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text=t("gui.date_hdr_cb"), variable=self.date_hdr).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(g, text=t("gui.sect_hdr_cb"), variable=self.sect_hdr).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(g, text=t("gui.placeholders_cb"),
                        variable=self.placeholders).grid(row=2, column=0, columnspan=4, sticky="w")

    def _on_remove(self):
        """Handle the remove event."""
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
        """Execute the add vk row operation."""
        row = VkExportRow(self.vk_list, self._remove_vk_row,
                          on_path_change=self._detect_senders)
        row.pack(fill="x", pady=4)
        self.vk_rows.append(row)
        if data:
            row.set(data)
        else:
            row.label_var.set(t("gui.vk_default_label", num=len(self.vk_rows)) if len(self.vk_rows) > 1 else t("gui.vk_default_label", num=""))

    def _remove_vk_row(self, row):
        """Execute the remove vk row operation."""
        if row in self.vk_rows:
            self.vk_rows.remove(row)
            row.destroy()

    # ---- TG rows ----
    def _add_tg_row(self, data: dict | None = None):
        """Execute the add tg row operation."""
        row = TgExportRow(self.tg_list, self._remove_tg_row,
                          on_path_change=self._detect_senders)
        row.pack(fill="x", pady=4)
        self.tg_rows.append(row)
        if data:
            row.set(data)
        else:
            n = len(self.tg_rows)
            row.label_var.set(t("gui.tg_default_label", num=n) if n > 1 else t("gui.tg_default_label", num=""))

    def _remove_tg_row(self, row):
        """Execute the remove tg row operation."""
        if row in self.tg_rows:
            self.tg_rows.remove(row)
            row.destroy()

    # ---- Bot rows ----
    def _add_bot_row(self, data: dict | None = None):
        """Execute the add bot row operation."""
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
        """Execute the remove bot row operation."""
        if row in self.bot_rows:
            self.bot_rows.remove(row)
            row.destroy()

    # ---- Detect senders ----
    def _detect_senders(self):
        """Auto-detect sender IDs/names from source files."""
        def work():
            """Execute the work operation."""
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
            vk_str = t("gui.vk_senders_found", senders=', '.join(sorted(vk_ids))) if vk_ids else ""
            tg_str = t("gui.tg_senders_found", senders=', '.join(sorted(tg_names))) if tg_names else ""
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
            "name": self.name_var.get().strip() or t("gui.task_default_name", num=self.task_index + 1),
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

    def from_task(self, task_data: dict):
        """Populate panel from a task dict."""
        task_data = normalize_task(task_data)
        name = task_data.get("name", t("gui.task_default_name", num=self.task_index + 1))
        # Dynamically translate the default task name if it matches standard patterns
        if name.startswith("Задача ") or name.startswith("Task "):
            try:
                num = int(name.split(" ")[1])
                name = t("gui.task_default_name", num=num)
            except ValueError:
                pass
        self.name_var.set(name)
        self.configure(text=self.name_var.get())
        self.mode_var.set(task_data.get("mode", MODE_VK_AND_TG))
        self.multichat_var.set(task_data.get("multichat", False))
        self.chat_var.set(str(task_data["target"]["chat_id"]))

        # VK exports
        for r in list(self.vk_rows):
            self._remove_vk_row(r)
        for ex in task_data["sources"].get("vk_exports") or []:
            self._add_vk_row(ex)

        # TG exports
        for r in list(self.tg_rows):
            self._remove_tg_row(r)
        for ex in task_data["sources"].get("telegram_exports") or []:
            self._add_tg_row(ex)

        # Bots
        for r in list(self.bot_rows):
            self._remove_bot_row(r)
        sm = task_data.get("sender_map", {})
        dn = task_data.get("display_names", {})
        vk_map_inv: dict[str, list[str]] = {}
        for vid, bkey in (sm.get("vk") or {}).items():
            vk_map_inv.setdefault(bkey, []).append(str(vid))
        tg_map_inv: dict[str, list[str]] = {}
        for tname, bkey in (sm.get("telegram") or {}).items():
            tg_map_inv.setdefault(bkey, []).append(tname)

        for key, token in (task_data.get("bots") or {}).items():
            self._add_bot_row({
                "key": key,
                "token": token,
                "display_name": dn.get(key, ""),
                "vk_ids": vk_map_inv.get(key, []),
                "tg_names": tg_map_inv.get(key, []),
                "is_system": key == task_data.get("system_bot", ""),
                "is_default": key == sm.get("vk_default", "") or key == sm.get("telegram_default", ""),
            })

        # Attachments
        af = task_data.get("attachments_filter") or {}
        for k, v in self.att_vars.items():
            v.set(af.get(k, True))

        # Rate & behavior
        self.delay_var.set(str(task_data["rate"].get("min_interval_seconds", 1.5)))
        self.send_attempts_var.set(str(task_data["retry"].get("send_media_attempts", 6)))
        beh = task_data.get("behavior", {})
        self.date_hdr.set(beh.get("send_date_headers", True))
        self.sect_hdr.set(beh.get("send_section_headers", True))
        self.placeholders.set(beh.get("placeholders_for_missing", True))


# ---------------------------------------------------------------------------
#  Main application
# ---------------------------------------------------------------------------

class App:
    """Execute the App operation."""
    def __init__(self, root: tk.Tk):
        """Initialize the instance."""
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
        self._build_ui()
        self._poll()

    def _build_ui(self):
        """Build the dynamic language UI components."""
        if hasattr(self, 'header_frame'):
            self.header_frame.destroy()
        if hasattr(self, 'nb'):
            self.nb.destroy()
        
        self.root.title(t("gui.window_title"))
        self._build_header()
        self._build_notebook()
        self._load_from_file()

    def _change_lang(self, ev=None):
        """Handle language switch."""
        lang = "ru" if self.lang_var.get() == "Русский" else "en"
        if lang != get_lang():
            set_lang(lang)
            s = self._settings_from_ui()
            self._settings_to_ui(s)
            self._build_ui()
    # ---- styling ----------------------------------------------------
    def _style(self):
        """Execute the style operation."""
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
        """Execute the build header operation."""
        self.header_frame = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        self.header_frame.pack(fill="x")
        ttk.Label(self.header_frame, text="Replay", style="Header.TLabel").pack(side="left")
        self.var_summary = tk.StringVar(value="")
        ttk.Label(self.header_frame, textvariable=self.var_summary, style="Sub.TLabel").pack(
            side="left", padx=(12, 0))
            
        # Language switcher
        self.lang_var = tk.StringVar(value="Русский" if get_lang() == "ru" else "English")
        lang_cb = ttk.Combobox(self.header_frame, textvariable=self.lang_var, 
                               values=["Русский", "English"], 
                               state="readonly", width=10)
        lang_cb.pack(side="right")
        lang_cb.bind("<<ComboboxSelected>>", self._change_lang)

    def _build_notebook(self):
        """Execute the build notebook operation."""
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tab_run = ttk.Frame(self.nb, padding=8)
        self.tab_cfg = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_run, text=t("gui.tab_run"))
        self.nb.add(self.tab_cfg, text=t("gui.tab_settings"))

        self._build_run_tab()
        self._build_settings_tab()

    # ---- Run tab ----------------------------------------------------
    def _build_run_tab(self):
        # Task selector
        """Execute the build run tab operation."""
        sel = ttk.Frame(self.tab_run)
        sel.pack(fill="x", pady=(0, 6))
        ttk.Label(sel, text=t("gui.task_label")).pack(side="left")
        self.task_combo = ttk.Combobox(sel, state="readonly", width=30)
        self.task_combo.pack(side="left", padx=8)
        self.task_combo.bind("<<ComboboxSelected>>", self._on_task_selected)

        # Controls
        ctrl = ttk.Frame(self.tab_run)
        ctrl.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(ctrl, text=t("gui.btn_start"), style="Accent.TButton",
                                    command=self.on_start)
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_pause = ttk.Button(ctrl, text=t("gui.btn_pause"), command=self.on_pause, state="disabled")
        self.btn_skip = ttk.Button(ctrl, text=t("gui.btn_skip"), command=self.on_skip, state="disabled")
        self.btn_stop = ttk.Button(ctrl, text=t("gui.btn_stop"), command=self.on_stop, state="disabled")
        for b in (self.btn_pause, self.btn_skip, self.btn_stop):
            b.pack(side="left", padx=4)
        ttk.Separator(ctrl, orient="vertical").pack(side="left", fill="y", padx=10, pady=2)
        ttk.Button(ctrl, text=t("gui.btn_test"), command=self.on_verify).pack(side="left", padx=4)
        ttk.Button(ctrl, text=t("gui.btn_errors"), command=self.on_errors).pack(side="left", padx=4)
        ttk.Button(ctrl, text=t("gui.btn_log"), command=self.on_open_log).pack(side="left", padx=4)
        self.reset_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text=t("gui.btn_reset"), variable=self.reset_var).pack(
            side="right", padx=4)

        # Progress
        pf = ttk.LabelFrame(self.tab_run, text=t("gui.frame_progress"), padding=8)
        pf.pack(fill="x", pady=4)
        self.pbar = ttk.Progressbar(pf, mode="determinate", maximum=100)
        self.pbar.pack(fill="x", pady=(0, 6))
        self.lbl_prog = ttk.Label(pf, text="0 / 0 (0%)", font=FONT_BIG)
        self.lbl_prog.pack(anchor="w")
        row = ttk.Frame(pf)
        row.pack(fill="x", pady=6)
        self.var_phase = tk.StringVar(value=t("gui.lbl_phase") + " —")
        self.var_elapsed = tk.StringVar(value=t("gui.lbl_elapsed") + " —")
        self.var_eta = tk.StringVar(value=t("gui.lbl_eta") + " —")
        self.var_rate = tk.StringVar(value=t("gui.lbl_rate") + " —")
        for i, v in enumerate((self.var_phase, self.var_elapsed, self.var_eta, self.var_rate)):
            ttk.Label(row, textvariable=v).grid(row=0, column=i, sticky="w", padx=(0, 16))
        self.var_current = tk.StringVar(value=t("gui.lbl_current") + " —")
        ttk.Label(pf, textvariable=self.var_current, foreground="#444").pack(anchor="w")
        self.var_file = tk.StringVar(value=t("gui.lbl_file") + " —")
        ttk.Label(pf, textvariable=self.var_file, foreground="#777").pack(anchor="w", pady=(0, 4))
        sub = ttk.Frame(pf)
        sub.pack(fill="x")
        ttk.Label(sub, text=t("gui.lbl_vk"), width=4).grid(row=0, column=0, sticky="w")
        self.vk_bar = ttk.Progressbar(sub, maximum=100)
        self.vk_bar.grid(row=0, column=1, sticky="ew", padx=6)
        self.var_vk = tk.StringVar(value="0 / 0")
        ttk.Label(sub, textvariable=self.var_vk, width=14).grid(row=0, column=2)
        ttk.Label(sub, text=t("gui.lbl_tg"), width=4).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.tg_bar = ttk.Progressbar(sub, maximum=100)
        self.tg_bar.grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))
        self.var_tg = tk.StringVar(value="0 / 0")
        ttk.Label(sub, textvariable=self.var_tg, width=14).grid(row=1, column=2, pady=(4, 0))
        sub.columnconfigure(1, weight=1)

        # Stats + resources in one row
        mid = ttk.Panedwindow(self.tab_run, orient="vertical")
        mid.pack(fill="both", expand=True, pady=4)

        stats_f = ttk.LabelFrame(mid, text=t("gui.frame_stats"), padding=6)
        mid.add(stats_f, weight=1)
        self.stat_vars: dict[str, tk.StringVar] = {}
        items = [
            ("text", t("gui.stat_text")), ("photo", t("gui.stat_photo")), ("sticker", t("gui.stat_sticker")),
            ("voice", t("gui.stat_voice")), ("video", t("gui.stat_video")), ("document", t("gui.stat_document")),
            ("header", t("gui.stat_header")), ("placeholders", t("gui.stat_placeholders")),
            ("skipped", t("gui.stat_skipped")), ("errors", t("gui.stat_errors")), ("retries", t("gui.stat_retries")),
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

        res_f = ttk.LabelFrame(mid, text=t("gui.frame_resources"), padding=6)
        mid.add(res_f, weight=0)
        self.res_vars: dict[str, tk.StringVar] = {}
        res_items = [
            ("ram", "RAM"), ("cpu", "CPU"), ("threads", t("gui.res_threads")),
            ("downloads", t("gui.res_downloads")), ("flood", "429"),
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
        lf = ttk.LabelFrame(self.tab_run, text=t("gui.frame_log"), padding=4)
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
        """Execute the build settings tab operation."""
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
        ttk.Button(bf, text=t("gui.add_task_btn"),
                   command=self._add_task_panel).pack(side="left", padx=(0, 16))
        ttk.Separator(bf, orient="vertical").pack(side="left", fill="y", padx=4, pady=2)
        ttk.Button(bf, text=t("gui.save_settings_btn"), style="Accent.TButton",
                   command=self.on_save_settings).pack(side="left", padx=8)
        ttk.Button(bf, text=t("gui.reload_settings_btn"),
                   command=self._load_from_file).pack(side="left", padx=4)
        ttk.Button(bf, text=t("gui.open_settings_btn"),
                   command=self.on_open_settings).pack(side="left", padx=4)
        ttk.Button(bf, text=t("gui.validate_paths_btn"),
                   command=self.on_validate).pack(side="left", padx=4)

    # ---- Task panel management ----
    def _add_task_panel(self, task_data: dict | None = None) -> TaskPanel:
        """Execute the add task panel operation."""
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
        """Execute the remove task panel operation."""
        if len(self.task_panels) <= 1:
            messagebox.showinfo(t("gui.msg_tasks_title"), t("gui.msg_cannot_delete_last"))
            return
        if panel in self.task_panels:
            self.task_panels.remove(panel)
            panel.destroy()
            # Reindex
            for i, p in enumerate(self.task_panels):
                p.task_index = i
            self._update_task_combo()

    def _on_detect_senders(self, panel: TaskPanel = None):
        """Handle the detect senders event."""
        pass  # Detection happens inside TaskPanel

    def _update_task_combo(self):
        """Execute the update task combo operation."""
        names = [p.name_var.get() or t("gui.task_default_name", num=i + 1)
                 for i, p in enumerate(self.task_panels)]
        self.task_combo["values"] = names
        if names:
            idx = min(self.active_task_idx, len(names) - 1)
            self.task_combo.current(idx)
            self.active_task_idx = idx

    def _on_task_selected(self, event=None):
        """Handle the task selected event."""
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
        """Execute the load from file operation."""
        try:
            s = load_settings()
            self._settings_to_ui(s)
            # Apply first task
            if s["tasks"]:
                apply_task(s["tasks"][0], 0)
            self.log(t("gui.msg_settings_loaded"))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("gui.msg_error_title"), t("gui.msg_settings_load_err", err=e))

    def on_save_settings(self):
        """Handle the save settings event."""
        try:
            s = self._settings_from_ui()
            # Validate all tasks
            all_errs = []
            for i, t in enumerate(s.get("tasks", [])):
                errs = validate_task(t)
                if errs:
                    name = t.get("name", t("gui.task_default_name", num=i + 1))
                    all_errs.extend(f"[{name}] {e}" for e in errs)
            if all_errs:
                messagebox.showwarning(
                    t("gui.msg_check_title"),
                    t("gui.msg_saved_warnings") + "\n\n" + "\n".join(f"• {e}" for e in all_errs))
            path = save_settings(s)
            # Re-apply active task
            tasks = s.get("tasks", [])
            if self.active_task_idx < len(tasks):
                apply_task(tasks[self.active_task_idx], self.active_task_idx)
            self.var_summary.set(settings_summary(s))
            self.log(t("gui.msg_settings_saved_log", path=path))
            messagebox.showinfo(t("gui.msg_saved_title"), t("gui.msg_settings_saved", path=path))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("gui.msg_error_title"), str(e))

    def on_validate(self):
        """Handle the validate event."""
        s = self._settings_from_ui()
        all_errs = []
        for i, t in enumerate(s.get("tasks", [])):
            errs = validate_task(t)
            name = t.get("name", t("gui.task_default_name", num=i + 1))
            all_errs.extend(f"[{name}] {e}" for e in errs)
        if all_errs:
            messagebox.showwarning(t("gui.msg_check_title"), "\n".join(f"• {e}" for e in all_errs))
        else:
            messagebox.showinfo(t("gui.msg_check_title"), "Все пути и параметры в порядке ✓")

    def on_open_settings(self):
        """Handle the open settings event."""
        path = SETTINGS_FILE
        if not os.path.isfile(path):
            save_settings(default_settings(), path)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo(t("gui.msg_file_title"), path)

    # ---- logging ----------------------------------------------------
    def log(self, msg: str):
        """Execute the log operation."""
        self.logq.put(msg)

    def _drain_log(self):
        """Execute the drain log operation."""
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
        """Handle the start event."""
        if self.worker and self.worker.is_alive():
            return
        s = self._settings_from_ui()
        tasks = s.get("tasks", [])
        idx = self.active_task_idx
        if idx >= len(tasks):
            messagebox.showerror(t("gui.msg_error_title"), t("gui.msg_no_task_selected"))
            return
        task = tasks[idx]
        errs = validate_task(task)
        if errs:
            if not messagebox.askyesno(
                    t("gui.msg_warn_title"), t("gui.msg_settings_issues") + "\n\n" + "\n".join(f"• {e}" for e in errs) + "\n\n" + t("gui.msg_run_anyway")):
                return
        try:
            save_settings(s)
            apply_task(task, idx)
            self.var_summary.set(settings_summary(s))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(t("gui.msg_error_title"), str(e))
            return

        reset = self.reset_var.get()
        self._set_running(True)
        name = task.get("name", t("gui.task_default_name", num=idx + 1))
        self.log(t("gui.log_start", name=name))
        self.log(task_summary(task))

        def work():
            """Execute the work operation."""
            try:
                run_export.run(reset=reset, log=self.log)
            except Exception as e:  # noqa: BLE001
                self.log(t("gui.log_critical_err", err=e))
            finally:
                self.root.after(0, lambda: self._set_running(False))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def on_pause(self):
        """Handle the pause event."""
        if CONTROL.is_paused():
            CONTROL.resume()
            self.btn_pause.config(text=t("gui.btn_pause"))
            self.log(t("gui.log_resumed"))
        else:
            CONTROL.pause()
            self.btn_pause.config(text=t("gui.btn_resume"))
            self.log(t("gui.log_paused"))

    def on_skip(self):
        """Handle the skip event."""
        CONTROL.request_skip()
        self.log(t("gui.log_skip_req"))

    def on_stop(self):
        """Handle the stop event."""
        if messagebox.askyesno(t("gui.msg_stop_title"), t("gui.msg_stop_confirm")):
            CONTROL.request_stop()
            self.log(t("gui.log_stop_req"))

    def on_verify(self):
        """Handle the verify event."""
        if self.verify_proc and self.verify_proc.poll() is None:
            return
        # Apply active task first
        s = self._settings_from_ui()
        tasks = s.get("tasks", [])
        idx = self.active_task_idx
        if idx < len(tasks):
            apply_task(tasks[idx], idx)
        self.log(t("gui.log_verify"))
        env = dict(os.environ, PYTHONIOENCODING="utf-8")

        def work():
            """Execute the work operation."""
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
        """Handle the open log event."""
        try:
            os.startfile(config.LOG_FILE)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo(t("gui.msg_log_title"), config.LOG_FILE)

    # ---- error window -----------------------------------------------
    def on_errors(self):
        """Handle the errors event."""
        if self.err_win is not None and tk.Toplevel.winfo_exists(self.err_win):
            self.err_win.deiconify()
            self.err_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title(t("gui.err_win_title"))
        win.geometry("760x420")
        self.err_win = win
        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        self.err_count_var = tk.StringVar(value="0")
        ttk.Label(top, textvariable=self.err_count_var, font=FONT_BOLD).pack(side="left")
        ttk.Button(top, text=t("gui.btn_clear"), command=self._clear_error_window).pack(side="right")
        cols = ("time", "type", "msg")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c, w in (("time", 160), ("type", 80), ("msg", 480)):
            tree.heading(c, text={"time": t("gui.err_col_time"), "type": t("gui.err_col_type"), "msg": t("gui.err_col_msg")}[c])
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
        """Execute the clear error window operation."""
        if self.err_tree:
            for iid in self.err_tree.get_children():
                self.err_tree.delete(iid)
        self.err_shown = 0

    def _refresh_error_window(self):
        """Execute the refresh error window operation."""
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
        self.err_count_var.set(t("gui.err_count", count=len(evs)))

    def _set_running(self, running: bool):
        """Configure the running."""
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_pause.config(state="normal" if running else "disabled")
        self.btn_skip.config(state="normal" if running else "disabled")
        self.btn_stop.config(state="normal" if running else "disabled")
        # Don't lock the settings tab — allow editing other tasks while running
        self.task_combo.config(state="disabled" if running else "readonly")
        if not running:
            self.btn_pause.config(text=t("gui.btn_pause"))

    def _poll(self):
        """Execute the poll operation."""
        self._drain_log()
        s = CONTROL.stats.snapshot()
        total, idx = s["total"], s["index"]
        pct = (idx / total * 100) if total else 0
        self.pbar.config(maximum=max(1, total), value=idx)
        self.lbl_prog.config(text=f"{idx:,} / {total:,} ({pct:.1f}%)".replace(",", " "))
        self.var_phase.set(f"{t('gui.lbl_phase')} {s['phase']}")
        self.var_elapsed.set(f"{t('gui.lbl_elapsed')} {fmt_dur(s['elapsed'])}")
        self.var_eta.set(f"{t('gui.lbl_eta')} {fmt_dur(s['eta'])}")
        self.var_rate.set(t("gui.rate_fmt", rate=s['rate'] * 60))
        self.var_current.set(f"{t('gui.lbl_current')} {s['current']}")
        cf = s.get("current_file") or "—"
        self.var_file.set(f"{t('gui.lbl_file')} {cf}  ({s.get('current_kind', '')})")
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
    """Execute the main operation."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
