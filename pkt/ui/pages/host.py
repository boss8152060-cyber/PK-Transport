"""The page of one module (PKT Data / PKT Train / PKT Analyze): the module's own page when it is installed, else a note with the
Install button. The page of the module is created the first time it is shown (a module can be slow to load, e.g. PKT Analyze)."""
import traceback
import tkinter as tk
from tkinter import ttk

from pkt.ui.kit import Card, autowrap
from pkt.ui.pages.home import glyph_tile
from pkt.ui.theme import COLORS, F

GLYPHS = {"data": "▣", "train": "◈", "analyze": "◫"}


class ModuleHost(ttk.Frame):
    def __init__(self, parent, app, mid):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.mid = mid
        self.page = None                                  # the module's page once it was created
        self.error = ""
        self.banner = tk.Frame(self, bg=COLORS["warn_soft"])          # "restart to use the new version" (only when needed)
        self.banner_label = tk.Label(self.banner, text="", bg=COLORS["warn_soft"], fg=COLORS["text"], font=F(10), anchor="w")
        self.banner_label.pack(side="left", padx=16, pady=8)
        self.b.button(self.banner, "mod_restart_now", app.restart_app, style="Compact.TButton").pack(side="right", padx=16, pady=6)
        self.holder = ttk.Frame(self)
        self.holder.pack(fill="both", expand=True)
        self.note = ttk.Frame(self.holder)
        self._build_note()
        app.refreshers.append(self.refresh)
        app.b.on_change(self.refresh)                       # the note is redrawn in the new language

    # ---------------------------------------------------------------- the note shown when there is no page
    def _build_note(self):
        wrap = ttk.Frame(self.note, padding=(30, 30, 30, 30))
        wrap.pack(fill="both", expand=True)
        card = Card(wrap)
        card.pack(anchor="nw", fill="x")
        c = card.inner
        top = ttk.Frame(c, style="Card.TFrame")
        top.pack(fill="x")
        glyph_tile(top, GLYPHS.get(self.mid, "▣"), 46).pack(side="left")
        ttk.Label(top, text=self.app.name_of(self.mid), style="Title.TLabel", background=COLORS["card"]).pack(side="left", padx=(14, 0))
        self.note_text = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c)
        self.note_text.pack(anchor="w", pady=(16, 0))
        self.note_detail = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
        self.note_detail.pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(c, style="Card.TFrame")
        row.pack(anchor="w", pady=(18, 0))
        self.install_btn = self.b.button(row, "mod_install", lambda: self.app.install_module(self.mid), style="Primary.TButton")
        self.install_btn.pack(side="left")
        self.b.button(row, "mod_open_manager", lambda: self.app.show("modules")).pack(side="left", padx=8)

    def _show_note(self, text, detail="", can_install=False):
        if self.page is not None:
            self.page.pack_forget()
        self.note.pack(fill="both", expand=True)
        self.note_text.configure(text=text)
        self.note_detail.configure(text=detail)
        self.install_btn.configure(state="normal" if (can_install and not self.app.mod_busy) else "disabled")

    # ---------------------------------------------------------------- state
    def refresh(self):
        app, mid = self.app, self.mid
        st = app.state_of(mid)
        busy = mid in app.mod_busy
        if mid in app.restart_needed and self.page is not None:
            self.banner_label.configure(text=app.t("mod_restart_needed", name=app.name_of(mid)))
            self.banner.pack(fill="x", before=self.holder)
        else:
            self.banner.pack_forget()
        if self.page is not None and st["installed"] and not st["problem"] and mid not in app.restart_needed:
            return
        if self.page is not None:
            return                                           # the old version stays on screen until the restart
        if busy:
            self._show_note(app.t("mod_working", name=app.name_of(mid)), app.mod_log[-1] if app.mod_log else "")
        elif not st["installed"]:
            self._show_note(app.t("host_not_installed", name=app.name_of(mid)), app.t("host_not_installed_note"), can_install=True)
        elif st["problem"]:
            self._show_note(app.t("host_problem", name=app.name_of(mid)), st["problem"])
        elif self.error:
            self._show_note(app.t("module_load_failed", name=app.name_of(mid), err=self.error), "", can_install=False)
        elif app.current == mid:                              # shown right now (a hidden module is not loaded)
            self._create()

    def on_show(self):
        self.refresh()
        if self.page is not None and hasattr(self.page, "on_show"):
            self.page.on_show()

    def _create(self):
        app, mid = self.app, self.mid
        st = app.state_of(mid)
        mod = app.plugin_of(mid)
        if mod is None:
            self.error = app.plugin_errors.get(mid, "?")
            self._show_note(app.t("module_load_failed", name=app.name_of(mid), err=self.error), "")
            return
        try:
            self.page = mod.create(self.holder, app, st["folder"])
        except Exception:                                    # a module that cannot build its page must not break the window
            self.error = traceback.format_exc(limit=4)
            self.page = None
            self._show_note(app.t("module_load_failed", name=app.name_of(mid), err=self.error), "")
            return
        self.error = ""
        self.note.pack_forget()
        self.page.pack(fill="both", expand=True)
        app.xl.areas.append(self.page)
        if hasattr(self.page, "on_show"):
            self.page.on_show()
        app.xl.sweep()

    # ---------------------------------------------------------------- what the window asks of every module
    def is_running(self):
        fn = getattr(self.page, "is_running", None)
        return bool(fn and fn())

    def stop_for_exit(self):
        fn = getattr(self.page, "stop_for_exit", None)
        if fn:
            fn()
