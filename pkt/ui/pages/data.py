"""PKT Data inside this window: the six workspaces of PKT Data (Data, Label, Curate, Analytics, Zone, Other) as sub-tabs.

The code stays in the PKT-Data repo: its `src` folder is put on sys.path and its tab classes are created inside this page the first
time the page is shown (so the window starts fast and a missing/broken PKT Data only breaks this page)."""
import os
import sys
import tkinter as tk
import traceback
from tkinter import ttk

from pkt.ui import theme
from pkt.ui.theme import COLORS, F

SUBTABS = [
    ("data", "Data", "pk_studio.ui.tabs.tab_data", "DataTab", "Import videos and build image datasets"),
    ("autolabeler", "Label", "pk_studio.ui.tabs.tab_autolabeler", "AutoLabelerTab", "Annotate and review objects"),
    ("curator_splitter", "Curate", "pk_studio.ui.tabs.tab_curator_splitter", "CuratorSplitterTab", "Select, balance and split data"),
    ("analytics", "Analytics", "pk_studio.ui.tabs.tab_analytics", "AnalyticsTab", "Understand dataset quality and shape"),
    ("zone_editor", "Zone", "pk_studio.ui.tabs.tab_zone_editor", "ZoneEditorTab", "Draw polygon zones on video frames"),
    ("other", "Other", "pk_studio.ui.tabs.tab_other", "OtherTab", "Extra video utilities"),
]


class DataPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.loaded = False
        self.error = None
        self.tabs = {}
        self.buttons = {}
        self.current = None
        bar = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=COLORS["card"])
        inner.pack(fill="x", padx=18, pady=10)
        tk.Label(inner, text="PKT Data", bg=COLORS["card"], fg=COLORS["text"], font=F(12, "bold")).pack(side="left", padx=(0, 18))
        for key, label, *_rest in SUBTABS:
            btn = ttk.Button(inner, text=label, style="Compact.TButton", command=lambda k=key: self.show_tab(k))
            btn.pack(side="left", padx=(0, 6))
            self.buttons[key] = btn
        self.body = tk.Frame(self, bg=COLORS["bg"])
        self.body.pack(fill="both", expand=True)
        self.message = ttk.Label(self.body, text="", style="Muted.TLabel", justify="left", wraplength=800)

    # ---------------------------------------------------------------- loading
    def on_show(self):
        if not self.loaded:
            self.load()
        if self.current is None and self.tabs:
            self.show_tab(SUBTABS[0][0])
        elif self.current:
            self.show_tab(self.current)

    def _fail(self, text):
        self.error = text
        self.message.configure(text=text)
        self.message.pack(anchor="nw", padx=30, pady=30)

    def load(self):
        self.loaded = True
        _d, info = self.app.info_of("data")
        src = os.path.join(info["folder"], "src")
        if not os.path.isdir(os.path.join(src, "pk_studio")):
            self._fail(self.app.t("module_missing", name="PKT Data", path=info["folder"]))
            return
        if src not in sys.path:
            sys.path.insert(0, src)
        try:
            import importlib
            from pk_studio.theme import apply_global_theme
            classes = {key: getattr(importlib.import_module(mod), cls) for key, _l, mod, cls, _h in SUBTABS}
            apply_global_theme(self.app.root)               # the styles the PKT Data tabs use ...
            theme.apply_theme(self.app.root)                # ... and then this window's own on top (same colours)
            for key, cls in classes.items():
                self.tabs[key] = cls(self.body)
        except Exception:                                   # a missing library, a broken checkout ...
            for tab in self.tabs.values():
                tab.destroy()
            self.tabs = {}
            self._fail(self.app.t("data_load_failed", err=traceback.format_exc(limit=3)))

    def show_tab(self, key):
        if key not in self.tabs:
            return
        self.current = key
        for tab in self.tabs.values():
            tab.pack_forget()
        self.tabs[key].pack(fill="both", expand=True)
        for k, btn in self.buttons.items():
            btn.configure(style="CompactPrimary.TButton" if k == key else "Compact.TButton")
