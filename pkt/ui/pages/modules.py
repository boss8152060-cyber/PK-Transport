"""The Modules page: install, update, switch the version of and uninstall PKT Data / PKT Train / PKT Analyze, one by one or all together."""
import tkinter as tk
from tkinter import ttk

from pkt import modman
from pkt.ui.kit import Card, Chip, ScrollFrame, autowrap, page_header
from pkt.ui.pages.home import glyph_tile
from pkt.ui.theme import COLORS, F

GLYPHS = {"data": "▣", "train": "◈", "analyze": "◫"}


class ModulesPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.rows = {}
        self._log_shown = 0
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = ttk.Frame(scroll.body, padding=(30, 26, 30, 30))
        body.pack(fill="both", expand=True)

        def right(holder):
            self.b.button(holder, "mod_check", self._check).pack(side="left")

        page_header(body, self.b, "modules_title", "modules_sub", right=right).pack(fill="x")
        self.legacy_card = Card(body)
        lc = self.legacy_card.inner
        self.b.label(lc, "mod_legacy_title", style="CardTitle.TLabel").pack(anchor="w")
        self.legacy_text = autowrap(ttk.Label(lc, text="", style="CardMuted.TLabel", justify="left"), lc)
        self.legacy_text.pack(anchor="w", pady=(6, 10))
        self.b.button(lc, "mod_legacy_open", lambda: app.open_path(app.project_root), style="Compact.TButton").pack(anchor="w")
        self._legacy_shown = False
        for d in app.defs:
            self._build_row(body, d)

        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(4, 12))
        self.update_all_btn = self.b.button(bar, "mod_update_all", app.update_all, style="Primary.TButton")
        self.update_all_btn.pack(side="left")
        self.install_missing_btn = self.b.button(bar, "mod_install_missing", app.install_missing)
        self.install_missing_btn.pack(side="left", padx=8)
        self.busy_label = ttk.Label(bar, text="", style="Muted.TLabel")
        self.busy_label.pack(side="left", padx=10)

        card = Card(body)
        card.pack(fill="x")
        self.b.label(card.inner, "mod_log", style="CardTitle.TLabel").pack(anchor="w")
        frame = ttk.Frame(card.inner, style="Card.TFrame")
        frame.pack(fill="x", pady=(8, 0))
        self.log = tk.Text(frame, height=10, wrap="word", state="disabled", bg=COLORS["field"], fg=COLORS["text"], relief="flat", font=("Consolas", 9),
                           highlightthickness=1, highlightbackground=COLORS["border"])
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")

        app.refreshers.append(self.refresh)
        app.b.on_change(self.refresh)

    # ---------------------------------------------------------------- one card per module
    def _build_row(self, body, d):
        app, mid = self.app, d["id"]
        card = Card(body)
        card.pack(fill="x", pady=(16, 0))
        c = card.inner
        top = ttk.Frame(c, style="Card.TFrame")
        top.pack(fill="x")
        glyph_tile(top, GLYPHS.get(mid, "▣"), 40).pack(side="left")
        ttk.Label(top, text=d["name"], style="CardTitle.TLabel").pack(side="left", padx=(12, 0))
        chip = Chip(top, "", "neutral")
        chip.pack(side="right")
        autowrap(self.b.label(c, d.get("desc_key", f"{mid}_desc"), style="CardMuted.TLabel", justify="left"), c).pack(anchor="w", pady=(10, 0))
        info = autowrap(ttk.Label(c, text="", style="Card.TLabel", justify="left"), c)
        info.pack(anchor="w", pady=(10, 0))
        newer = autowrap(ttk.Label(c, text="", style="CardMuted.TLabel", justify="left"), c)
        newer.pack(anchor="w", pady=(2, 0))
        ctl = ttk.Frame(c, style="Card.TFrame")
        ctl.pack(anchor="w", pady=(14, 0))
        self.b.label(ctl, "mod_version_label", style="CardMuted.TLabel").pack(side="left", padx=(0, 8))
        var = tk.StringVar(value="")
        combo = ttk.Combobox(ctl, textvariable=var, state="readonly", width=16)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda e, m=mid: self.refresh())
        main_btn = self.b.button(ctl, "mod_install", lambda m=mid: self._main_action(m), style="CompactPrimary.TButton")
        main_btn.pack(side="left", padx=(12, 0))
        upd_btn = self.b.button(ctl, "mod_update", lambda m=mid: app.update_module(m), style="Compact.TButton")
        upd_btn.pack(side="left", padx=(8, 0))
        un_btn = self.b.button(ctl, "mod_uninstall", lambda m=mid: app.uninstall_module(m), style="Compact.TButton")
        un_btn.pack(side="left", padx=(8, 0))
        open_btn = self.b.button(ctl, "open_folder", lambda m=mid: self._open_folder(m), style="Compact.TButton")
        open_btn.pack(side="left", padx=(8, 0))
        self.rows[mid] = {"chip": chip, "info": info, "newer": newer, "var": var, "combo": combo, "main": main_btn, "update": upd_btn, "uninstall": un_btn,
                          "open": open_btn, "values": []}

    # ---------------------------------------------------------------- actions
    def _check(self):
        self.app.check_updates()

    def _selected_tag(self, mid):
        """The tag chosen in the list: None = the newest version."""
        row = self.rows[mid]
        idx = row["combo"].current()
        tags = self.app.tags.get(mid) or []
        if idx <= 0 or idx - 1 >= len(tags):
            return None
        return tags[idx - 1]["tag"]

    def _main_action(self, mid):
        app = self.app
        tag = self._selected_tag(mid)
        st = app.state_of(mid)
        if st["installed"] and tag is not None and tag != st["tag"]:
            from tkinter import messagebox
            version = next((t["version"] for t in app.tags.get(mid, []) if t["tag"] == tag), tag)
            if not messagebox.askyesno(app.t("app_title"), app.t("mod_confirm_switch", name=app.name_of(mid), old=st["version"], new=version), parent=app.root):
                return
        app.install_module(mid, tag)

    def _open_folder(self, mid):
        st = self.app.state_of(mid)
        if st["installed"]:
            self.app.open_path(st["folder"])

    # ---------------------------------------------------------------- redraw
    def refresh(self):
        app = self.app
        busy = bool(app.mod_busy)
        for mid, row in self.rows.items():
            st = app.state_of(mid)
            tags = app.tags.get(mid) or []
            # the version list: "latest" first, then every released version
            latest = app.t("mod_latest") + (f" ({tags[0]['version']})" if tags else "")
            values = [latest] + [t["version"] for t in tags]
            if values != row["values"]:
                keep = row["combo"].current()
                row["combo"].configure(values=values)
                row["values"] = values
                row["combo"].current(keep if 0 <= keep < len(values) else 0)
            elif row["combo"].current() < 0:
                row["combo"].current(0)
            res = app.updates.get(mid) or {}
            if mid in app.mod_busy:
                chip, kind = "⏳ " + app.t("mod_working", name=app.name_of(mid)), "neutral"
            elif st["problem"]:
                chip, kind = "⚠ " + app.t("mod_incompatible"), "bad"
            elif not st["installed"]:
                chip, kind = app.t("mod_not_installed"), "neutral"
            elif res.get("state") == "behind":
                chip, kind = "⬇ " + app.t("mod_update_available", new=res["remote"]), "warn"
            else:
                chip, kind = "✓ " + app.t("mod_installed", version=st["version"] or "-"), "ok"
            row["chip"].configure(text=chip)
            row["chip"].set_kind(kind)
            if st["linked"]:
                row["info"].configure(text=app.t("mod_linked", path=st["folder"]))
            elif st["installed"]:
                row["info"].configure(text=app.t("mod_info_installed", version=st["version"] or "-", folder=st["folder"]) + (f"\n⚠ {st['problem']}" if st["problem"] else ""))
            else:
                row["info"].configure(text=app.t("mod_info_none") + (f"\n⚠ {st['problem']}" if st["problem"] else ""))
            err = app.tag_errors.get(mid)
            row["newer"].configure(text=app.t("mod_tags_failed", msg=err) if err and not tags else "")
            tag = self._selected_tag(mid) if row["values"] else None
            switching = st["installed"] and tag is not None and tag != st["tag"]
            if st["installed"]:
                row["main"].configure(text=app.t("mod_switch") if switching else app.t("mod_reinstall"))
            else:
                row["main"].configure(text=app.t("mod_install"))
            can_use = not busy and not st["linked"]
            row["main"].configure(state="normal" if can_use else "disabled")
            row["update"].configure(state="normal" if (can_use and res.get("state") == "behind") else "disabled")
            row["uninstall"].configure(state="normal" if (can_use and st["installed"]) else "disabled")
            row["open"].configure(state="normal" if st["installed"] else "disabled")
        self.update_all_btn.configure(state="normal" if (not busy and any((app.updates.get(m) or {}).get("state") == "behind" for m in self.rows)) else "disabled")
        self.install_missing_btn.configure(state="normal" if (not busy and any(not app.state_of(m)["installed"] for m in self.rows)) else "disabled")
        self.busy_label.configure(text=app.t("mod_busy_note") if busy else "")
        legacy = modman.legacy_folders(app.project_root)
        if legacy:
            self.legacy_text.configure(text=app.t("mod_legacy_note", names=", ".join(legacy)))
            if not self._legacy_shown:
                self.legacy_card.pack(fill="x", pady=(16, 0), after=self.legacy_card.master.winfo_children()[0])
                self._legacy_shown = True
        elif self._legacy_shown:
            self.legacy_card.pack_forget()
            self._legacy_shown = False
        self._fill_log()

    def _fill_log(self):
        lines = self.app.mod_log
        if self._log_shown == len(lines):
            return
        self.log.configure(state="normal")
        for line in lines[self._log_shown:]:
            self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self._log_shown = len(lines)

    def on_show(self):
        if not self.app.tags and not self.app.checking:
            self.app.fetch_tags()
        self.refresh()
