"""The PK Transport window: one card per module (PKT Data, PKT Train, PKT Analyze) with its status, version and an Open button."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pkt import __version__, shared, shortcut, updates
from pkt.i18n import LANGS, LANG_NAMES, Translator
from pkt.modules import (ROOT, SETTINGS_FILE, DEFAULT_MODULES_FILE, build_command, load_module_defs, load_settings,
                         read_version, resolve_module, save_settings)

LOG_DIR = os.path.join(ROOT, "logs")
EARLY_EXIT_CHECK_MS = 2500          # a module that has closed (with an error) this soon after starting is reported with its log


class Launcher:
    def __init__(self, root, settings_path=SETTINGS_FILE, defs_path=DEFAULT_MODULES_FILE, project_root=ROOT):
        self.root = root
        self.settings_path = settings_path
        self.project_root = project_root
        self.defs = load_module_defs(defs_path)
        self.settings = load_settings(settings_path)
        self.tr = Translator(self.settings.get("language", "th"))
        self.status_var = tk.StringVar(value="")
        self.lang_var = tk.StringVar(value=self.tr.lang)
        self.cards = {}                 # module id -> dict of the widgets/vars of its card
        self.procs = {}                 # module id -> the Popen of the last start
        self.train_page = None          # the open PKT Train window
        self.updates = {}               # module id (or 'app') -> result of updates.check_repo
        self.checking = False
        self.update_q = queue.Queue()   # results from the update threads (Tk is only touched from the main thread)
        self.app_update_var = tk.StringVar(value="")
        root.minsize(900, 420)
        root.geometry("1040x470")
        self.body = ttk.Frame(root, padding=14)
        self.body.pack(fill="both", expand=True)
        self.build()
        root.after(300, self._poll_updates)
        if self.settings.get("auto_check_updates", True):
            self.check_updates()

    # ---------------------------------------------------------------- texts / language
    def t(self, key, **kw):
        return self.tr.t(key, **kw)

    def set_language(self, lang):
        if lang not in LANGS:
            return
        self.tr.set_lang(lang)
        self.lang_var.set(lang)
        self.settings["language"] = lang
        self._save()
        self.build()
        if self.train_page is not None:
            self.train_page.retranslate()

    def _save(self):
        try:
            save_settings(self.settings, self.settings_path)
        except OSError:
            pass

    # ---------------------------------------------------------------- window
    def build(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.cards = {}
        self.root.title(f"{self.t('app_title')} {__version__}")

        head = ttk.Frame(self.body)
        head.pack(fill="x")
        left = ttk.Frame(head)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text=self.t("app_title"), font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(left, text=self.t("subtitle"), font=("Segoe UI", 11)).pack(anchor="w")
        right = ttk.Frame(head)
        right.pack(side="right")
        ttk.Label(right, text=self.t("language")).grid(row=0, column=0, padx=(0, 6))
        for i, lang in enumerate(LANGS):
            ttk.Radiobutton(right, text=LANG_NAMES[lang], value=lang, variable=self.lang_var,
                            command=lambda lg=lang: self.set_language(lg)).grid(row=0, column=1 + i, padx=2)
        ttk.Button(right, text=self.t("settings"), command=self.open_settings).grid(row=0, column=3, padx=(12, 0))
        ttk.Button(right, text=self.t("updates_check"), command=self.check_updates).grid(row=1, column=1, columnspan=3, sticky="e", pady=(6, 0))
        self.app_update_btn = ttk.Button(right, text=self.t("updates_update"), command=lambda: self.update_module("app"), state="disabled")
        self.app_update_btn.grid(row=2, column=3, sticky="e", pady=(4, 0))
        ttk.Label(right, textvariable=self.app_update_var, foreground="#555555").grid(row=2, column=0, columnspan=3, sticky="e", pady=(4, 0))

        ttk.Label(self.body, text=self.t("pipeline_hint"), foreground="#555555").pack(anchor="w", pady=(8, 8))

        grid = ttk.Frame(self.body)
        grid.pack(fill="both", expand=True)
        for c in range(len(self.defs)):
            grid.columnconfigure(c, weight=1, uniform="cards")
        for c, mod_def in enumerate(self.defs):
            self._build_card(grid, c, mod_def)

        ttk.Label(self.body, textvariable=self.status_var, foreground="#1f4e79").pack(anchor="w", pady=(8, 0))
        self.refresh()

    def _build_card(self, parent, column, mod_def):
        mid = mod_def["id"]
        card = ttk.LabelFrame(parent, text=f" {mod_def['name']} ", padding=12)
        card.grid(row=0, column=column, sticky="nsew", padx=6, pady=4)
        desc = ttk.Label(card, text=self.t(f"{mid}_desc"), wraplength=260, justify="left")
        desc.pack(anchor="w")
        ttk.Separator(card).pack(fill="x", pady=8)
        status = tk.Label(card, text="", anchor="w", font=("Segoe UI", 10, "bold"))
        status.pack(anchor="w")
        version = ttk.Label(card, text="", justify="left")
        version.pack(anchor="w", pady=(2, 0))
        detail = ttk.Label(card, text="", justify="left", foreground="#555555", wraplength=260)
        detail.pack(anchor="w")
        folder = ttk.Label(card, text="", justify="left", foreground="#777777", wraplength=260)
        folder.pack(anchor="w", pady=(4, 0))
        note = ttk.Label(card, text="", justify="left", foreground="#8a5a00", wraplength=260)
        note.pack(anchor="w", pady=(6, 0))
        upd = ttk.Label(card, text="", justify="left", wraplength=260)
        upd.pack(anchor="w", pady=(6, 0))
        buttons = ttk.Frame(card)
        buttons.pack(side="bottom", anchor="w", pady=(10, 0))
        open_btn = ttk.Button(buttons, text=self.t("open"), command=lambda m=mid: self.launch(m))
        open_btn.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text=self.t("open_folder"), command=lambda m=mid: self.open_folder(m)).grid(row=0, column=1)
        upd_btn = ttk.Button(buttons, text=self.t("updates_update"), command=lambda m=mid: self.update_module(m), state="disabled")
        upd_btn.grid(row=0, column=2, padx=(6, 0))
        self.cards[mid] = {"status": status, "version": version, "detail": detail, "folder": folder, "note": note, "open": open_btn,
                           "update": upd, "update_btn": upd_btn}

    def info_of(self, mid):
        mod_def = next(d for d in self.defs if d["id"] == mid)
        return mod_def, resolve_module(mod_def, self.settings, self.project_root)

    def refresh(self):
        """Fill every card from the disk: found / not found, version, branch, folder."""
        for mod_def in self.defs:
            mid = mod_def["id"]
            info = resolve_module(mod_def, self.settings, self.project_root)
            ver = read_version(info, mod_def)
            card = self.cards[mid]
            ok = info["exists"] and (info["entry_exists"] or not info["launchable"])
            card["status"].config(text=("● " + self.t("found")) if ok else ("● " + self.t("missing")), fg="#1b7f3b" if ok else "#b00020")
            card["version"].config(text=f"{self.t('version')}: {ver['version'] or '-'}")
            parts = []
            if ver["branch"]:
                parts.append(f"{self.t('branch')}: {ver['branch']} · {ver['commit']}")
            if ver["dirty"]:
                parts.append("⚠ " + self.t("changes"))
            if info["exists"] and not ver["git"]:
                parts.append(self.t("git_missing"))
            card["detail"].config(text="\n".join(parts))
            card["folder"].config(text=info["folder"])
            note = ""
            if mid == "analyze" and shared.get_analyze_model(self.settings):
                note = self.t("analyze_model_set", name=os.path.basename(shared.get_analyze_model(self.settings)))
            card["note"].config(text=note)
            card["open"].config(state=("normal" if (info["launchable"] and info["entry_exists"]) else "disabled"))
        self._show_updates()

    # ---------------------------------------------------------------- actions
    def _open_path(self, path):
        if os.name == "nt":
            os.startfile(path)                      # noqa: S606 (the user's own folder)
        else:
            subprocess.Popen(["xdg-open", path])

    def open_folder(self, mid):
        mod_def, info = self.info_of(mid)
        if not info["exists"]:
            messagebox.showerror(self.t("app_title"), self.t("module_missing", name=info["name"], path=info["folder"]), parent=self.root)
            return False
        self._open_path(info["folder"])
        return True

    def launch(self, mid):
        """Start a module as its own program (its own window); returns the Popen or None."""
        mod_def, info = self.info_of(mid)
        name = info["name"]
        if not info["exists"]:
            messagebox.showerror(self.t("app_title"), self.t("module_missing", name=name, path=info["folder"]), parent=self.root)
            return None
        if not info["launchable"]:
            return None
        if mod_def.get("page") == "train":
            return self.open_train_page(info["folder"])
        if not info["entry_exists"]:
            messagebox.showerror(self.t("app_title"), self.t("entry_missing", name=name, path=info["entry_path"]), parent=self.root)
            return None
        cmd = build_command(info)
        if not cmd:
            messagebox.showerror(self.t("app_title"), self.t("python_missing", name=name), parent=self.root)
            return None
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"{mid}.log")
        try:
            log = open(log_path, "ab")
            env = shared.analyze_environment(self.settings) if mid == "analyze" else None     # PKT Analyze gets the chosen model (PKT_MODEL_PATH)
            proc = subprocess.Popen(cmd, cwd=info["folder"], env=env, stdout=log, stderr=subprocess.STDOUT)
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), f"{self.t('launch_failed', name=name)}\n\n{exc}", parent=self.root)
            return None
        self.procs[mid] = proc
        self.status_var.set(self.t("opened", name=name))
        self.root.after(EARLY_EXIT_CHECK_MS, lambda: self._check_early_exit(mid, name, proc, log_path))
        return proc

    def open_train_page(self, folder):
        """The PKT Train page (a window of this app, not a separate program)."""
        from pkt.train_page import TrainPage
        if self.train_page is not None:
            try:
                self.train_page.top.deiconify()
                self.train_page.top.lift()
                return self.train_page
            except tk.TclError:
                self.train_page = None
        self.train_page = TrainPage(self, folder)
        self.status_var.set(self.t("opened", name="PKT Train"))
        return self.train_page

    def _check_early_exit(self, mid, name, proc, log_path):
        code = proc.poll()
        if code is not None and code != 0:
            messagebox.showerror(self.t("app_title"), self.t("exited_early", name=name, code=code, log=log_path), parent=self.root)

    # ---------------------------------------------------------------- settings
    # ---------------------------------------------------------------- updates (git)
    def _update_targets(self):
        """(id, folder) of every module that exists, and of this app."""
        out = []
        for mod_def in self.defs:
            info = resolve_module(mod_def, self.settings, self.project_root)
            if info["exists"]:
                out.append((mod_def["id"], info["folder"]))
        out.append(("app", self.project_root))
        return out

    def check_updates(self):
        """Look on GitHub for new commits of every module and of this app (in a thread; the result is shown by _poll_updates)."""
        if self.checking:
            return False
        self.checking = True
        self.app_update_var.set(self.t("updates_checking"))
        targets = self._update_targets()

        def work():
            for mid, folder in targets:
                self.update_q.put(("check", mid, updates.check_repo(folder)))
            self.update_q.put(("done", None, None))

        threading.Thread(target=work, daemon=True).start()
        return True

    def _poll_updates(self):
        try:
            if not self.root.winfo_exists() or not self.body.winfo_exists():
                return                              # the window (or this launcher's body) is gone: stop polling
        except tk.TclError:
            return
        changed = False
        try:
            while True:
                kind, mid, data = self.update_q.get_nowait()
                if kind == "check":
                    self.updates[mid] = data
                    changed = True
                elif kind == "done":
                    self.checking = False
                    changed = True
                elif kind == "pulled":
                    ok, msg = data
                    name = self._name_of(mid)
                    if ok:
                        self.status_var.set(self.t("updates_done", name=name) + (" — " + self.t("updates_restart") if mid == "app" else ""))
                        self.updates[mid] = updates.check_repo(self._folder_of(mid), fetch=False)
                    else:
                        messagebox.showerror(self.t("app_title"), self.t("updates_failed", name=name, msg=msg), parent=self.root)
                    changed = True
        except queue.Empty:
            pass
        if changed:
            self.refresh()
        self.root.after(300, self._poll_updates)

    def _name_of(self, mid):
        return self.t("app_self") if mid == "app" else next((d["name"] for d in self.defs if d["id"] == mid), mid)

    def _folder_of(self, mid):
        return self.project_root if mid == "app" else self.info_of(mid)[1]["folder"]

    def _update_text(self, res):
        """(text, colour) of an update-check result."""
        st = res["state"]
        if st == "uptodate":
            text, col = self.t("updates_uptodate"), "#1b7f3b"
        elif st == "behind":
            text, col = self.t("updates_behind", n=res["behind"]), "#b45f00"
        elif st == "ahead":
            text, col = self.t("updates_ahead", n=res["ahead"]), "#555555"
        elif st == "diverged":
            text, col = self.t("updates_diverged", ahead=res["ahead"], behind=res["behind"]), "#b00020"
        elif st == "no_git":
            text, col = self.t("updates_no_git"), "#777777"
        else:
            text, col = self.t("updates_no_upstream"), "#777777"
        if st in ("uptodate", "behind", "ahead", "diverged") and res.get("error"):
            text += " · " + self.t("updates_offline")
        return text, col

    def _show_updates(self):
        for mid, card in self.cards.items():
            res = self.updates.get(mid)
            if res is None or res["state"] == "missing":
                card["update"].config(text="")
                card["update_btn"].config(state="disabled")
                continue
            text, col = self._update_text(res)
            card["update"].config(text=text, foreground=col)
            card["update_btn"].config(state=("normal" if res["state"] == "behind" else "disabled"))
        res = self.updates.get("app")
        if self.checking and res is None:
            return
        if res is None or res["state"] == "missing":
            self.app_update_var.set("")
            self.app_update_btn.config(state="disabled")
        else:
            text, _col = self._update_text(res)
            self.app_update_var.set(f"{self.t('app_self')} {__version__}: " + text)
            self.app_update_btn.config(state=("normal" if res["state"] == "behind" else "disabled"))

    def update_module(self, mid):
        """Take the new commits of a module (or this app) with a fast-forward pull, after the user confirms."""
        res = self.updates.get(mid)
        if not res or res["state"] != "behind":
            return False
        folder = self._folder_of(mid)
        name = self._name_of(mid)
        log = chr(10).join(updates.incoming(folder)) or "-"
        if not messagebox.askyesno(self.t("app_title"), self.t("updates_confirm", name=name, log=log), parent=self.root):
            return False
        self.status_var.set(self.t("updates_checking"))
        threading.Thread(target=lambda: self.update_q.put(("pulled", mid, updates.pull_ff(folder))), daemon=True).start()
        return True

    def create_shortcut(self):
        ok, result = shortcut.create_shortcut(self.project_root)
        if ok:
            self.status_var.set(self.t("shortcut_done", path=result))
        else:
            messagebox.showerror(self.t("app_title"), self.t("shortcut_fail", msg=result), parent=self.root)
        return ok

    def open_settings(self):
        top = tk.Toplevel(self.root)
        top.title(self.t("settings_title"))
        top.transient(self.root)
        frame = ttk.Frame(top, padding=14)
        frame.pack(fill="both", expand=True)
        vars_ = {}
        for r, mod_def in enumerate(self.defs):
            mid = mod_def["id"]
            info = resolve_module(mod_def, self.settings, self.project_root)
            ttk.Label(frame, text=mod_def["name"], font=("Segoe UI", 10, "bold")).grid(row=r * 3, column=0, columnspan=3, sticky="w", pady=(8 if r else 0, 2))
            fv = tk.StringVar(value=info["folder"])
            pv = tk.StringVar(value=info["python"])
            vars_[mid] = (fv, pv)
            ttk.Label(frame, text=self.t("module_folder")).grid(row=r * 3 + 1, column=0, sticky="w")
            ttk.Entry(frame, textvariable=fv, width=70).grid(row=r * 3 + 1, column=1, padx=6, sticky="ew")
            ttk.Button(frame, text=self.t("browse"), command=lambda v=fv, n=mod_def["name"]: self._browse_folder(v, n, top)).grid(row=r * 3 + 1, column=2)
            if mod_def.get("entry"):
                ttk.Label(frame, text=self.t("python_command")).grid(row=r * 3 + 2, column=0, sticky="w")
                ttk.Entry(frame, textvariable=pv, width=70).grid(row=r * 3 + 2, column=1, padx=6, sticky="ew")
        frame.columnconfigure(1, weight=1)
        mrow = len(self.defs) * 3
        ttk.Label(frame, text=self.t("analyze_model"), font=("Segoe UI", 10, "bold")).grid(row=mrow, column=0, columnspan=3, sticky="w", pady=(12, 2))
        top.model_var = tk.StringVar(value=shared.get_analyze_model(self.settings))
        ttk.Entry(frame, textvariable=top.model_var, width=70).grid(row=mrow + 1, column=0, columnspan=2, sticky="ew", padx=(0, 6))
        mbtns = ttk.Frame(frame)
        mbtns.grid(row=mrow + 1, column=2)
        ttk.Button(mbtns, text=self.t("browse"), command=lambda: self._browse_model(top.model_var, top)).pack(side="left")
        ttk.Button(mbtns, text=self.t("clear"), command=lambda: top.model_var.set("")).pack(side="left", padx=(4, 0))
        top.auto_var = tk.BooleanVar(value=bool(self.settings.get("auto_check_updates", True)))
        ttk.Checkbutton(frame, text=self.t("auto_check"), variable=top.auto_var).grid(row=len(self.defs) * 3 + 2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(frame, text=self.t("shortcut_create"), command=self.create_shortcut).grid(row=len(self.defs) * 3 + 2, column=2, sticky="e", pady=(12, 0))
        bar = ttk.Frame(frame)
        bar.grid(row=len(self.defs) * 3 + 3, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(bar, text=self.t("save"), command=lambda: self._save_settings(vars_, top)).pack(side="left", padx=4)
        ttk.Button(bar, text=self.t("cancel"), command=top.destroy).pack(side="left")
        top.settings_vars = vars_
        return top

    def _browse_model(self, var, parent):
        path = filedialog.askopenfilename(parent=parent, title=self.t("choose_model_file"), filetypes=[("PyTorch model", "*.pt"), ("*", "*.*")],
                                          initialdir=os.path.dirname(var.get()) if var.get() else self.project_root)
        if path:
            var.set(os.path.normpath(path))

    def _browse_folder(self, var, name, parent):
        path = filedialog.askdirectory(parent=parent, title=self.t("pick_folder", name=name), initialdir=var.get() or self.project_root)
        if path:
            var.set(os.path.normpath(path))

    def _save_settings(self, vars_, top):
        """Keep only what differs from modules.json (a folder or a Python command the user typed)."""
        mods = {}
        for mod_def in self.defs:
            fv, pv = vars_[mod_def["id"]]
            default_folder = resolve_module(mod_def, {}, self.project_root)["folder"]
            entry = {}
            folder = os.path.normpath(fv.get().strip()) if fv.get().strip() else ""
            if folder and folder != default_folder:
                entry["path"] = folder
            if pv.get().strip():
                entry["python"] = pv.get().strip()
            if entry:
                mods[mod_def["id"]] = entry
        self.settings["modules"] = mods
        if getattr(top, "auto_var", None) is not None:
            self.settings["auto_check_updates"] = bool(top.auto_var.get())
        if getattr(top, "model_var", None) is not None:
            shared.set_analyze_model(self.settings, top.model_var.get().strip())
        self._save()
        top.destroy()
        self.status_var.set(self.t("saved"))
        self.refresh()


def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
