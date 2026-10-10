"""Settings page: language, update check, where the modules are and which Python starts them, desktop shortcut, about."""
import tkinter as tk
from tkinter import filedialog, ttk

from pkt import __version__
from pkt.i18n import LANGS, LANG_NAMES
from pkt.modules import resolve_module
from pkt.ui.kit import Card, ScrollFrame, autowrap, page_header


class SettingsPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = ttk.Frame(scroll.body, padding=(30, 26, 30, 30))
        body.pack(fill="both", expand=True)
        page_header(body, self.b, "settings_title", "settings_sub").pack(fill="x")

        # ---- language
        card = Card(body)
        card.pack(fill="x", pady=(20, 14))
        self.b.label(card.inner, "language", style="CardTitle.TLabel").pack(anchor="w")
        row = ttk.Frame(card.inner, style="Card.TFrame")
        row.pack(anchor="w", pady=(10, 0))
        for lang in LANGS:
            ttk.Radiobutton(row, text=LANG_NAMES[lang], value=lang, variable=app.lang_var, style="Card.TRadiobutton",
                            command=lambda lg=lang: app.set_language(lg)).pack(side="left", padx=(0, 20))
        self.b.label(card.inner, "language_note", style="CardSubtle.TLabel").pack(anchor="w", pady=(8, 0))

        # ---- updates
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        self.b.label(card.inner, "section_updates", style="CardTitle.TLabel").pack(anchor="w")
        self.auto_var = tk.BooleanVar(value=bool(app.settings.get("auto_check_updates", True)))
        self.b.check(card.inner, "auto_check", self.auto_var, command=self.save).pack(anchor="w", pady=(10, 0))
        row = ttk.Frame(card.inner, style="Card.TFrame")
        row.pack(anchor="w", pady=(10, 0))
        self.b.button(row, "updates_check", app.check_updates).pack(side="left")
        self.app_update_btn = self.b.button(row, "updates_update_app", lambda: app.update_module("app"), state="disabled")
        self.app_update_btn.pack(side="left", padx=8)
        ttk.Label(row, textvariable=app.app_update_var, style="CardMuted.TLabel").pack(side="left", padx=(6, 0))

        # ---- modules
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        c = card.inner
        c.columnconfigure(1, weight=1)
        self.b.label(c, "section_modules", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.b.label(c, "section_modules_note", style="CardSubtle.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.folder_vars, self.python_vars = {}, {}
        r = 2
        for mod_def in app.defs:
            mid = mod_def["id"]
            _d, info = app.info_of(mid)
            self.folder_vars[mid] = tk.StringVar(value=info["folder"])
            self.python_vars[mid] = tk.StringVar(value=info["python"])
            ttk.Label(c, text=mod_def["name"], style="Card.TLabel", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=3, sticky="w", pady=(14, 2))
            self.b.label(c, "module_folder", style="CardMuted.TLabel").grid(row=r + 1, column=0, sticky="w", padx=(0, 14))
            ttk.Entry(c, textvariable=self.folder_vars[mid]).grid(row=r + 1, column=1, sticky="ew", padx=(0, 8))
            self.b.button(c, "browse", lambda m=mid: self._browse_folder(m)).grid(row=r + 1, column=2)
            self.b.label(c, "python_command", style="CardMuted.TLabel").grid(row=r + 2, column=0, sticky="w", padx=(0, 14), pady=(6, 0))
            ttk.Entry(c, textvariable=self.python_vars[mid]).grid(row=r + 2, column=1, sticky="ew", padx=(0, 8), pady=(6, 0))
            r += 3
        self.b.button(c, "save", self.save, style="Primary.TButton").grid(row=r, column=0, sticky="w", pady=(16, 0))

        # ---- shortcut + about
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        self.b.label(card.inner, "section_shortcut", style="CardTitle.TLabel").pack(anchor="w")
        self.b.label(card.inner, "shortcut_note", style="CardMuted.TLabel").pack(anchor="w", pady=(6, 0))
        self.b.button(card.inner, "shortcut_create", app.create_shortcut).pack(anchor="w", pady=(10, 0))

        card = Card(body)
        card.pack(fill="x")
        self.b.label(card.inner, "section_about", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card.inner, text=f"PK Transport {__version__}", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        autowrap(self.b.label(card.inner, "about_text", style="CardMuted.TLabel", justify="left"), card.inner).pack(anchor="w", pady=(4, 0))
        app.refreshers.append(self.sync)

    def sync(self):
        """Show the folders / Python commands the settings really hold (after an update or a change elsewhere)."""
        res = self.app.updates.get("app")
        self.app_update_btn.configure(state="normal" if (res and res["state"] == "behind") else "disabled")
        for mod_def in self.app.defs:
            mid = mod_def["id"]
            if mid in self.folder_vars:
                info = resolve_module(mod_def, self.app.settings, self.app.project_root)
                if self.folder_vars[mid].get() != info["folder"] and not self.focus_get():
                    self.folder_vars[mid].set(info["folder"])

    def _browse_folder(self, mid):
        path = filedialog.askdirectory(parent=self.app.root, title=self.app.t("pick_folder", name=self.app.name_of(mid)), initialdir=self.folder_vars[mid].get() or self.app.project_root)
        if path:
            import os
            self.folder_vars[mid].set(os.path.normpath(path))

    def save(self):
        self.app.save_modules_settings({m: v.get() for m, v in self.folder_vars.items()}, {m: v.get() for m, v in self.python_vars.items()}, self.auto_var.get())
