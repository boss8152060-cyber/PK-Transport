"""Home page: the workflow (Data -> Train -> Analyze), one card per module with its state, and the recent work."""
import os
import time
import tkinter as tk
from tkinter import ttk

from pkt import shared
from pkt.ui.kit import Card, Chip, ScrollFrame, autowrap, page_header
from pkt.ui.theme import COLORS, F

MODULES = [("data", "▣", "PKT Data", "data_desc"), ("train", "◈", "PKT Train", "train_desc"), ("analyze", "◫", "PKT Analyze", "analyze_desc")]


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

        # workflow
        self.b.label(body, "home_workflow", style="Section.TLabel").pack(anchor="w", pady=(22, 8))
        flow = ttk.Frame(body)
        flow.pack(fill="x")
        for i, (mid, glyph, name, _d) in enumerate(MODULES):
            flow.columnconfigure(i * 2, weight=1, uniform="step")
            card = Card(flow, padding=12, cursor="hand2")
            card.grid(row=0, column=i * 2, sticky="ew")
            row = ttk.Frame(card.inner, style="Card.TFrame")
            row.pack(fill="x")
            ttk.Label(row, text=f"0{i + 1}", style="CardSubtle.TLabel", font=("Consolas", 10, "bold")).pack(side="left")
            ttk.Label(row, text=name, style="CardTitle.TLabel").pack(side="left", padx=(10, 0))
            self.b.label(card.inner, f"home_step_{mid}", style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))
            for w in (card, card.inner, row) + tuple(row.winfo_children()) + tuple(card.inner.winfo_children()):
                w.bind("<Button-1>", lambda e, m=mid: self.app.show(m))
            if i < len(MODULES) - 1:
                ttk.Label(flow, text="›", font=F(18), foreground=COLORS["subtle"]).grid(row=0, column=i * 2 + 1, padx=8)

        # modules
        self.b.label(body, "home_modules", style="Section.TLabel").pack(anchor="w", pady=(24, 8))
        grid = ttk.Frame(body)
        grid.pack(fill="x")
        for i, (mid, glyph, name, desc_key) in enumerate(MODULES):
            grid.columnconfigure(i, weight=1, uniform="mod")
            card = Card(grid)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == len(MODULES) - 1 else 7))
            c = card.inner
            top = ttk.Frame(c, style="Card.TFrame")
            top.pack(fill="x")
            glyph_tile(top, glyph).pack(side="left")
            ttk.Label(top, text=name, style="CardTitle.TLabel").pack(side="left", padx=(12, 0))
            chip = Chip(top, "", "ok")
            chip.pack(side="right")
            btns = ttk.Frame(c, style="Card.TFrame")
            btns.pack(side="bottom", anchor="w", pady=(14, 0))          # the buttons of the three cards line up at the bottom
            autowrap(self.b.label(c, desc_key, style="CardMuted.TLabel", justify="left"), c).pack(anchor="w", pady=(12, 10))
            ttk.Separator(c).pack(fill="x", pady=(0, 10))
            version = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c)
            version.pack(anchor="w")
            metric = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
            metric.pack(anchor="w", pady=(4, 0))
            upd = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
            upd.pack(anchor="w", pady=(4, 0))
            open_btn = self.b.button(btns, "open", lambda m=mid: self.app.launch(m), style="CompactPrimary.TButton")
            open_btn.grid(row=0, column=0, padx=(0, 8))
            self.b.button(btns, "open_folder", lambda m=mid: self.app.open_folder(m), style="Compact.TButton").grid(row=0, column=1)
            upd_btn = self.b.button(btns, "updates_update", lambda m=mid: self.app.update_module(m), style="Compact.TButton", state="disabled")
            upd_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            self.cards[mid] = {"chip": chip, "version": version, "metric": metric, "update": upd, "open": open_btn, "update_btn": upd_btn}

        # recent work
        self.b.label(body, "home_recent", style="Section.TLabel").pack(anchor="w", pady=(24, 8))
        self.recent_card = Card(body)
        self.recent_card.pack(fill="x")
        self.recent_rows = ttk.Frame(self.recent_card.inner, style="Card.TFrame")
        self.recent_rows.pack(fill="x")

        app.refreshers.append(self.refresh)
        app.b.on_change(self.refresh)

    # ---------------------------------------------------------------- data of the cards
    def _train_summary(self):
        folder = self.app.info_of("train")[1]["folder"]
        runs = shared.find_runs(os.path.join(folder, "Runs"))
        self.runs = runs
        if not runs:
            return self.app.t("home_train_none")
        best = max((r["map50_95"] for r in runs if r["map50_95"] is not None), default=None)
        text = self.app.t("home_train_runs", n=len(runs))
        if best is not None:
            text += " · " + self.app.t("home_best_map", m=f"{best:.3f}")
        return text

    def _analyze_summary(self):
        _d, info = self.app.info_of("analyze")
        outs = shared.find_analysis_outputs(os.path.join(os.path.dirname(info["folder"]), "Output"))
        self.outputs = outs
        model = shared.get_analyze_model(self.app.settings)
        text = self.app.t("home_model", name=os.path.basename(model) if model else self.app.t("home_model_default"))
        if outs:
            text += " · " + self.app.t("home_results", n=len(outs))
        return text

    def refresh(self):
        app = self.app
        self.runs, self.outputs = [], []
        summaries = {"data": lambda: "", "train": self._train_summary, "analyze": self._analyze_summary}
        behind = 0
        for mid, card in self.cards.items():
            _d, info = app.info_of(mid)
            ver = app.versions.get(mid) or {}
            ok = info["exists"] and (info["entry_exists"] or not info["launchable"])
            card["chip"].configure(text=("✓ " + app.t("found")) if ok else ("⚠ " + app.t("missing")))
            card["chip"].set_kind("ok" if ok else "bad")
            card["version"].configure(text=f"{app.t('version')}: {ver.get('version') or '-'}" + (f"  ·  {ver['branch']} {ver['commit']}" if ver.get("branch") else ""))
            card["metric"].configure(text=summaries[mid]() if ok else info["folder"])
            res = app.updates.get(mid)
            if res is None or res["state"] == "missing":
                card["update"].configure(text="")
                card["update_btn"].configure(state="disabled")
            else:
                text, kind = app.update_text(res)
                prefix = {"ok": "✓ ", "warn": "⬇ ", "bad": "⚠ "}.get(kind, "")
                card["update"].configure(text=prefix + text)
                card["update_btn"].configure(state="normal" if res["state"] == "behind" else "disabled")
                behind += 1 if res["state"] == "behind" else 0
            card["open"].configure(state="normal" if (info["launchable"] and info["entry_exists"]) else "disabled")
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
        self._fill_recent()

    def _fill_recent(self):
        for w in self.recent_rows.winfo_children():
            w.destroy()
        items = []
        for r in getattr(self, "runs", [])[:5]:
            items.append((r["mtime"], "◈", self.app.t("home_recent_run", run=r["run"], model=r["model"] or r["family"]),
                          f"mAP50-95 {r['map50_95']:.3f}" if r["map50_95"] is not None else ""))
        for o in getattr(self, "outputs", [])[:5]:
            meta = []
            if o["ttc"] is not None:
                meta.append(f"TTC {o['ttc']}")
            if o["pet"] is not None:
                meta.append(f"PET {o['pet']}")
            items.append((o["mtime"], "◫", self.app.t("home_recent_analysis", name=o["clip"] or o["name"]), " · ".join(meta)))
        items.sort(key=lambda x: x[0], reverse=True)
        if not items:
            ttk.Label(self.recent_rows, text=self.app.t("home_recent_none"), style="CardMuted.TLabel").pack(anchor="w")
            return
        for i, (mtime, glyph, title, meta) in enumerate(items[:6]):
            row = ttk.Frame(self.recent_rows, style="Card.TFrame")
            row.pack(fill="x", pady=(0 if i == 0 else 8, 0))
            ttk.Label(row, text=glyph, style="Card.TLabel", font=("Segoe UI Symbol", 12)).pack(side="left", padx=(0, 10))
            ttk.Label(row, text=title, style="Card.TLabel").pack(side="left")
            ttk.Label(row, text=time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)), style="CardSubtle.TLabel").pack(side="right")
            if meta:
                ttk.Label(row, text=meta, style="CardMuted.TLabel").pack(side="right", padx=(0, 16))
