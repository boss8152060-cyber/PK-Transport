"""Home page: the workflow (Data -> Train -> Analyze), one card per module with its state, and the recent work."""
import time
import tkinter as tk
from tkinter import ttk

from pkt.ui.kit import Card, Chip, ScrollFrame, autowrap, page_header
from pkt.ui.theme import COLORS, F

GLYPHS = {"data": "▣", "train": "◈", "analyze": "◫"}


def glyph_tile(parent, glyph, size=36):
    tile = tk.Frame(parent, bg=COLORS["accent"], width=size, height=size)
    tile.pack_propagate(False)
    tk.Label(tile, text=glyph, bg=COLORS["accent"], fg="#FFFFFF", font=("Segoe UI Symbol", 14)).place(relx=.5, rely=.5, anchor="center")
    return tile


class HomePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.cards = {}
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = ttk.Frame(scroll.body, padding=(30, 26, 30, 30))
        body.pack(fill="both", expand=True)

        def right(holder):
            self.update_chip = Chip(holder, "", "neutral")
            self.update_chip.pack(side="left", padx=(0, 10))
            self.b.button(holder, "updates_check", self.app.check_updates).pack(side="left")

        page_header(body, self.b, "home_title", "subtitle", right=right).pack(fill="x")

        # nothing installed yet: say what to do
        self.empty_card = Card(body)
        c = self.empty_card.inner
        self.b.label(c, "home_empty_title", style="CardTitle.TLabel").pack(anchor="w")
        autowrap(self.b.label(c, "home_empty_text", style="CardMuted.TLabel", justify="left"), c).pack(anchor="w", pady=(6, 10))
        self.b.button(c, "home_empty_button", lambda: self.app.show("modules"), style="Primary.TButton").pack(anchor="w")

        # workflow
        self.b.label(body, "home_workflow", style="Section.TLabel").pack(anchor="w", pady=(22, 8))
        flow = ttk.Frame(body)
        flow.pack(fill="x")
        defs = app.defs
        for i, d in enumerate(defs):
            mid = d["id"]
            flow.columnconfigure(i * 2, weight=1, uniform="step")
            card = Card(flow, padding=12, cursor="hand2")
            card.grid(row=0, column=i * 2, sticky="ew")
            row = ttk.Frame(card.inner, style="Card.TFrame")
            row.pack(fill="x")
            ttk.Label(row, text=f"0{i + 1}", style="CardSubtle.TLabel", font=("Consolas", 10, "bold")).pack(side="left")
            ttk.Label(row, text=d["name"], style="CardTitle.TLabel").pack(side="left", padx=(10, 0))
            self.b.label(card.inner, f"home_step_{mid}", style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))
            for w in (card, card.inner, row) + tuple(row.winfo_children()) + tuple(card.inner.winfo_children()):
                w.bind("<Button-1>", lambda e, m=mid: self.app.show(m))
            if i < len(defs) - 1:
                ttk.Label(flow, text="›", font=F(18), foreground=COLORS["subtle"]).grid(row=0, column=i * 2 + 1, padx=8)

        # modules
        self.b.label(body, "home_modules", style="Section.TLabel").pack(anchor="w", pady=(24, 8))
        grid = ttk.Frame(body)
        grid.pack(fill="x")
        for i, d in enumerate(defs):
            mid = d["id"]
            grid.columnconfigure(i, weight=1, uniform="mod")
            card = Card(grid)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == len(defs) - 1 else 7))
            c = card.inner
            top = ttk.Frame(c, style="Card.TFrame")
            top.pack(fill="x")
            glyph_tile(top, GLYPHS.get(mid, "▣")).pack(side="left")
            ttk.Label(top, text=d["name"], style="CardTitle.TLabel").pack(side="left", padx=(12, 0))
            chip = Chip(top, "", "ok")
            chip.pack(side="right")
            btns = ttk.Frame(c, style="Card.TFrame")
            btns.pack(side="bottom", anchor="w", pady=(14, 0))          # the buttons of the cards line up at the bottom
            autowrap(self.b.label(c, d.get("desc_key", f"{mid}_desc"), style="CardMuted.TLabel", justify="left"), c).pack(anchor="w", pady=(12, 10))
            ttk.Separator(c).pack(fill="x", pady=(0, 10))
            version = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c)
            version.pack(anchor="w")
            metric = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
            metric.pack(anchor="w", pady=(4, 0))
            upd = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
            upd.pack(anchor="w", pady=(4, 0))
            open_btn = self.b.button(btns, "open", lambda m=mid: self._open_or_install(m), style="CompactPrimary.TButton")
            open_btn.grid(row=0, column=0, padx=(0, 8))
            self.b.button(btns, "modules_manage", lambda: self.app.show("modules"), style="Compact.TButton").grid(row=0, column=1)
            upd_btn = self.b.button(btns, "updates_update", lambda m=mid: self.app.update_module(m), style="Compact.TButton", state="disabled")
            upd_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            self.cards[mid] = {"chip": chip, "version": version, "metric": metric, "update": upd, "open": open_btn, "update_btn": upd_btn}

        # recent work
        self.b.label(body, "home_recent", style="Section.TLabel").pack(anchor="w", pady=(24, 8))
        self.recent_card = Card(body)
        self.recent_card.pack(fill="x")
        self.recent_rows = ttk.Frame(self.recent_card.inner, style="Card.TFrame")
        self.recent_rows.pack(fill="x")
        self._body = body
        self._empty_shown = False

        app.refreshers.append(self.refresh)
        app.b.on_change(self.refresh)

    def _open_or_install(self, mid):
        if self.app.module_ready(mid):
            self.app.show(mid)
        elif not self.app.state_of(mid)["installed"]:
            self.app.install_module(mid)
        else:
            self.app.show("modules")

    # ---------------------------------------------------------------- data of the cards
    def _summary(self, mid):
        mod = self.app.plugin_of(mid)
        if mod is None or not hasattr(mod, "summary"):
            return ""
        try:
            return mod.summary(self.app, self.app.state_of(mid)["folder"]) or ""
        except Exception:                                   # a module's summary must not break Home
            return ""

    def _recent(self):
        items = []
        for d in self.app.defs:
            mod = self.app.plugins.get(d["id"])
            if mod is not None and hasattr(mod, "recent"):
                try:
                    items += mod.recent(self.app, self.app.state_of(d["id"])["folder"]) or []
                except Exception:
                    pass
        return items

    def refresh(self):
        app = self.app
        behind = 0
        installed_any = False
        for mid, card in self.cards.items():
            st = app.state_of(mid)
            installed_any = installed_any or st["installed"]
            busy = mid in app.mod_busy
            if busy:
                card["chip"].configure(text="⏳ " + app.t("mod_working", name=app.name_of(mid)))
                card["chip"].set_kind("neutral")
            elif st["problem"]:
                card["chip"].configure(text="⚠ " + app.t("mod_incompatible"))
                card["chip"].set_kind("bad")
            elif st["installed"]:
                card["chip"].configure(text="✓ " + app.t("mod_installed_short"))
                card["chip"].set_kind("ok")
            else:
                card["chip"].configure(text=app.t("mod_not_installed"))
                card["chip"].set_kind("neutral")
            card["version"].configure(text=f"{app.t('version')}: {st['version']}" if st["installed"] else app.t("home_not_installed_hint"))
            card["metric"].configure(text=self._summary(mid) if (st["installed"] and not st["problem"]) else (st["problem"] or ""))
            res = app.updates.get(mid)
            if res is None or res["state"] == "missing":
                card["update"].configure(text="")
                card["update_btn"].configure(state="disabled")
            else:
                text, kind = app.update_text(res)
                prefix = {"ok": "✓ ", "warn": "⬇ ", "bad": "⚠ "}.get(kind, "")
                card["update"].configure(text=prefix + text)
                card["update_btn"].configure(state="normal" if (res["state"] == "behind" and not app.mod_busy) else "disabled")
                behind += 1 if res["state"] == "behind" else 0
            ready = app.module_ready(mid)
            self.b.rebind(card["open"], "open" if ready else "mod_install")
            card["open"].configure(state="disabled" if (busy or app.mod_busy and not ready) else "normal")
        app_res = app.updates.get("app")
        if app_res and app_res["state"] == "behind":
            behind += 1
        if app.checking and not app.updates:
            self.update_chip.configure(text=app.t("updates_checking"))
            self.update_chip.set_kind("neutral")
        elif behind:
            self.update_chip.configure(text="⬇ " + app.t("home_updates_available", n=behind))
            self.update_chip.set_kind("warn")
        else:
            self.update_chip.configure(text="✓ " + app.t("updates_uptodate"))
            self.update_chip.set_kind("ok")
        if installed_any and self._empty_shown:
            self.empty_card.pack_forget()
            self._empty_shown = False
        elif not installed_any and not self._empty_shown:
            self.empty_card.pack(fill="x", pady=(18, 0), after=self._body.winfo_children()[0])
            self._empty_shown = True
        self._fill_recent()

    def _fill_recent(self):
        for w in self.recent_rows.winfo_children():
            w.destroy()
        items = sorted(self._recent(), key=lambda x: x["mtime"], reverse=True)
        if not items:
            ttk.Label(self.recent_rows, text=self.app.t("home_recent_none"), style="CardMuted.TLabel").pack(anchor="w")
            return
        for i, it in enumerate(items[:6]):
            row = ttk.Frame(self.recent_rows, style="Card.TFrame")
            row.pack(fill="x", pady=(0 if i == 0 else 8, 0))
            ttk.Label(row, text=it.get("glyph", "•"), style="Card.TLabel", font=("Segoe UI Symbol", 12)).pack(side="left", padx=(0, 10))
            ttk.Label(row, text=it["title"], style="Card.TLabel").pack(side="left")
            ttk.Label(row, text=time.strftime("%Y-%m-%d %H:%M", time.localtime(it["mtime"])), style="CardSubtle.TLabel").pack(side="right")
            if it.get("meta"):
                ttk.Label(row, text=it["meta"], style="CardMuted.TLabel").pack(side="right", padx=(0, 16))
