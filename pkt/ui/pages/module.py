"""A module page (PKT Data / PKT Analyze): what it does, its state and version, update, Open; PKT Analyze also shows the model it starts with."""
import os
import tkinter as tk
from tkinter import filedialog, ttk

from pkt import shared
from pkt.ui.kit import Card, Chip, ScrollFrame, autowrap
from pkt.ui.pages.home import glyph_tile
from pkt.ui.theme import COLORS, F

GLYPHS = {"data": "▣", "train": "◈", "analyze": "◫"}


class ModulePage(ttk.Frame):
    def __init__(self, parent, app, mid):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.mid = mid
        self.name = {"data": "PKT Data", "analyze": "PKT Analyze", "train": "PKT Train"}[mid]
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = ttk.Frame(scroll.body, padding=(30, 26, 30, 30))
        body.pack(fill="both", expand=True)

        head = ttk.Frame(body)
        head.pack(fill="x")
        glyph_tile(head, GLYPHS[mid], 46).pack(side="left")
        titles = ttk.Frame(head)
        titles.pack(side="left", padx=(14, 0))
        ttk.Label(titles, text=self.name, style="Title.TLabel").pack(anchor="w")
        autowrap(self.b.label(titles, f"{mid}_desc", style="Subtitle.TLabel", justify="left"), body, pad=100).pack(anchor="w", pady=(2, 0))

        # ---- state
        card = Card(body)
        card.pack(fill="x", pady=(20, 14))
        c = card.inner
        c.columnconfigure(1, weight=1)
        top = ttk.Frame(c, style="Card.TFrame")
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.b.label(top, "section_status", style="CardTitle.TLabel").pack(side="left")
        self.chip = Chip(top, "", "ok")
        self.chip.pack(side="left", padx=(12, 0))
        rows = [("version", "version"), ("branch", "branch"), ("folder_label", "module_folder")]
        self.value_labels = {}
        for i, (name, key) in enumerate(rows, start=1):
            self.b.label(c, key, style="CardMuted.TLabel").grid(row=i, column=0, sticky="nw", pady=(10, 0), padx=(0, 18))
            lab = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c, pad=190)
            lab.grid(row=i, column=1, sticky="w", pady=(10, 0))
            self.value_labels[name] = lab
        self.b.label(c, "updates_check", style="CardMuted.TLabel").grid(row=4, column=0, sticky="nw", pady=(10, 0), padx=(0, 18))
        self.update_label = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c, pad=190)
        self.update_label.grid(row=4, column=1, sticky="w", pady=(10, 0))
        btns = ttk.Frame(c, style="Card.TFrame")
        btns.grid(row=5, column=0, columnspan=3, sticky="w", pady=(18, 0))
        self.open_btn = self.b.button(btns, "open_program", lambda: self.app.launch(mid), style="Primary.TButton")
        self.open_btn.pack(side="left")
        self.b.button(btns, "open_folder", lambda: self.app.open_folder(mid)).pack(side="left", padx=8)
        self.update_btn = self.b.button(btns, "updates_update", lambda: self.app.update_module(mid), state="disabled")
        self.update_btn.pack(side="left")

        # ---- what it does
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        self.b.label(card.inner, "section_about", style="CardTitle.TLabel").pack(anchor="w")
        autowrap(self.b.label(card.inner, f"about_{mid}", style="Card.TLabel", justify="left"), card.inner).pack(anchor="w", pady=(8, 0))

        # ---- the model (PKT Analyze)
        if mid == "analyze":
            card = Card(body)
            card.pack(fill="x", pady=(0, 14))
            c = card.inner
            c.columnconfigure(0, weight=1)
            self.b.label(c, "analyze_model", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
            self.model_var = tk.StringVar(value="")
            ttk.Entry(c, textvariable=self.model_var).grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(10, 0))
            self.b.button(c, "browse", self.browse_model).grid(row=1, column=1, pady=(10, 0))
            self.b.button(c, "clear", lambda: self.model_var.set("")).grid(row=1, column=2, padx=(8, 0), pady=(10, 0))
            row = ttk.Frame(c, style="Card.TFrame")
            row.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))
            self.b.button(row, "save", self.save_model, style="Primary.TButton").pack(side="left")
            self.b.button(row, "model_goto_train", lambda: self.app.show("train")).pack(side="left", padx=8)
            autowrap(self.b.label(c, "model_hint", style="CardSubtle.TLabel", justify="left"), c).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        autowrap(self.b.label(body, "module_note_separate", style="Muted.TLabel", justify="left"), body).pack(anchor="w", pady=(4, 0))
        app.refreshers.append(self.refresh)
        app.b.on_change(self.refresh)

    # ---------------------------------------------------------------- model of PKT Analyze
    def browse_model(self):
        cur = self.model_var.get()
        path = filedialog.askopenfilename(parent=self.app.root, title=self.app.t("choose_model_file"), filetypes=[("PyTorch model", "*.pt"), ("*", "*.*")],
                                          initialdir=os.path.dirname(cur) if cur else self.app.project_root)
        if path:
            self.model_var.set(os.path.normpath(path))

    def save_model(self):
        ok = self.app.set_analyze_model(self.model_var.get().strip())
        self.app.set_status("model_saved" if ok else "model_cleared")
        return ok

    # ---------------------------------------------------------------- redraw
    def on_show(self):
        self.refresh()

    def refresh(self):
        app = self.app
        _d, info = app.info_of(self.mid)
        ver = app.versions.get(self.mid) or {}
        ok = info["exists"] and (info["entry_exists"] or not info["launchable"])
        self.chip.configure(text=("✓ " + app.t("found")) if ok else ("⚠ " + app.t("missing")))
        self.chip.set_kind("ok" if ok else "bad")
        self.value_labels["version"].configure(text=ver.get("version") or "-")
        branch = f"{ver['branch']} · {ver['commit']}" if ver.get("branch") else "-"
        if ver.get("dirty"):
            branch += "   ⚠ " + app.t("changes")
        self.value_labels["branch"].configure(text=branch)
        self.value_labels["folder_label"].configure(text=info["folder"])
        res = app.updates.get(self.mid)
        if res is None or res["state"] == "missing":
            self.update_label.configure(text="-")
            self.update_btn.configure(state="disabled")
        else:
            text, kind = app.update_text(res)
            self.update_label.configure(text={"ok": "✓ ", "warn": "⬇ ", "bad": "⚠ "}.get(kind, "") + text)
            self.update_btn.configure(state="normal" if res["state"] == "behind" else "disabled")
        self.open_btn.configure(state="normal" if (info["launchable"] and info["entry_exists"]) else "disabled")
        if self.mid == "analyze":
            self.model_var.set(shared.get_analyze_model(app.settings))
