"""PK Transport main window: a navigation rail on the left, one page at a time on the right (Home, PKT Data, PKT Train, PKT Analyze, Settings).

The logic that was in the first launcher (open a module as its own program, check GitHub for updates, the settings file) lives here;
the pages only draw and call these methods."""
import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from pkt import __version__, shared, shortcut, updates
from pkt.i18n import LANGS, LANG_NAMES, Translator
from pkt.modules import (DEFAULT_MODULES_FILE, ROOT, SETTINGS_FILE, build_command, load_module_defs, load_settings, read_version,
                         resolve_module, save_settings)
from pkt.ui import theme
from pkt.ui.bind import TextBinder
from pkt.ui.kit import SidebarItem
from pkt.ui.theme import COLORS, F

LOG_DIR = os.path.join(ROOT, "logs")
EARLY_EXIT_CHECK_MS = 2500          # a module that closes (with an error) this soon after starting is reported with its log
NAV = [("home", "\u2302", "nav_home", "nav_hint_home"), ("data", "\u25A3", None, "nav_hint_data"), ("train", "\u25C8", None, "nav_hint_train"),
       ("analyze", "\u25EB", None, "nav_hint_analyze"), ("settings", "\u2699", "nav_settings", "nav_hint_settings")]
MODULE_NAMES = {"data": "PKT Data", "train": "PKT Train", "analyze": "PKT Analyze"}


class PKTApp:
    def __init__(self, root, settings_path=SETTINGS_FILE, defs_path=DEFAULT_MODULES_FILE, project_root=ROOT):
        self.root = root
        self.settings_path = settings_path
        self.project_root = project_root
        self.defs = load_module_defs(defs_path)
        self.settings = load_settings(settings_path)
        self.tr = Translator(self.settings.get("language", "th"))
        self.b = TextBinder(self.tr)
        self.status_var = tk.StringVar(value="")
        self.lang_var = tk.StringVar(value=self.tr.lang)
        self.procs = {}                 # module id -> the Popen of the last start
        self.versions = {}              # module id -> read_version(...) (git calls are done on refresh_modules, not on every redraw)
        self.updates = {}               # module id (or 'app') -> result of updates.check_repo
        self.checking = False
        self.update_q = queue.Queue()   # results of the update threads (Tk is only touched from the main thread)
        self.refreshers = []            # functions the pages register: called when module data changed
        self.pages = {}
        self.nav_items = {}
        self.current = None

        root.title(f"PK Transport {__version__}")
        root.minsize(1000, 660)
        root.geometry("1220x780")
        theme.apply_theme(root)
        icon_path = os.path.join(project_root, "assets", "icon.ico")
        if os.path.isfile(icon_path):
            try:
                root.iconbitmap(icon_path)                  # the icon of PKT Data
            except tk.TclError:
                pass
        self._build_shell()
        self._build_pages()
        self._build_translator()
        self.refresh_modules()
        self.show("home")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(300, self._poll_updates)
        if self.settings.get("auto_check_updates", True):
            self.check_updates()

    def on_close(self):
        """Close the window; a training that is still running is stopped (it can be resumed later) after the user confirms."""
        train = self.pages.get("train")
        if train is not None and train.is_running():
            if not messagebox.askyesno(self.t("app_title"), self.t("train_busy_close"), parent=self.root):
                return
            train.stop_for_exit()
        analyze = self.pages.get("analyze")
        if analyze is not None and analyze.is_running():
            if not messagebox.askyesno(self.t("app_title"), self.t("analyze_busy_close"), parent=self.root):
                return
            analyze.stop_for_exit()
            self.root.after(800, self.root.destroy)             # the run ends after its current frame
            return
        self.root.destroy()

    # ================================================================ texts / language / settings
    def t(self, key, **kw):
        return self.tr.t(key, **kw)

    def name_of(self, mid):
        return self.t("app_self") if mid == "app" else MODULE_NAMES.get(mid, mid)

    def set_language(self, lang):
        if lang not in LANGS:
            return
        self.tr.set_lang(lang)
        self.lang_var.set(lang)
        self.settings["language"] = lang
        self._save()
        self.root.title(f"PK Transport {__version__}")
        self._paint_lang_switch()
        self.b.refresh()
        self._show_app_update()
        self.xl.sweep()                                   # PKT Data / PKT Analyze texts

    def _save(self):
        try:
            save_settings(self.settings, self.settings_path)
        except OSError:
            pass

    def set_status(self, key=None, **kw):
        self.status_var.set(self.t(key, **kw) if key else "")

    # ================================================================ shell
    def _build_shell(self):
        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        self.sidebar = tk.Frame(root, bg=COLORS["sidebar"], width=244)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"], height=92)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        logo = tk.Frame(brand, bg=COLORS["accent"], width=42, height=42)          # the PK mark of PKT Data
        logo.place(x=22, y=24)
        logo.pack_propagate(False)
        tk.Label(logo, text="PK", bg=COLORS["accent"], fg="#FFFFFF", font=F(12, "bold")).place(relx=.5, rely=.5, anchor="center")
        tk.Label(brand, text="PK Transport", bg=COLORS["sidebar"], fg=COLORS["sidebar_text"], font=F(14, "bold")).place(x=76, y=20)
        tk.Label(brand, text="TRAFFIC SAFETY STUDIO", bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"], font=F(7, "bold")).place(x=77, y=52)
        tk.Label(self.sidebar, text="WORKSPACE", bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"], font=F(8, "bold"), anchor="w").pack(fill="x", padx=20, pady=(9, 8))
        for page, glyph, key, hint in NAV:
            if page != "settings":
                self._add_nav(page, glyph, key, hint)
        tk.Frame(self.sidebar, bg=COLORS["sidebar"]).pack(fill="both", expand=True)
        self._add_nav("settings", "\u2699", "nav_settings", "nav_hint_settings")
        tk.Frame(self.sidebar, bg=COLORS["sidebar_line"], height=1).pack(fill="x", padx=18, pady=(12, 12))
        lang_row = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        lang_row.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(lang_row, text="\u25CE", font=("Segoe UI Symbol", 12), bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"]).pack(side="left", padx=(0, 8))
        self.lang_buttons = {}
        for lang in LANGS:
            lb = tk.Label(lang_row, text=LANG_NAMES[lang], font=F(9, "bold"), padx=10, pady=3, cursor="hand2")
            lb.pack(side="left", padx=(0, 4))
            lb.bind("<Button-1>", lambda e, lg=lang: self.set_language(lg))
            self.lang_buttons[lang] = lb
        self._paint_lang_switch()
        tk.Label(self.sidebar, text=f"v{__version__}", font=F(8), bg=COLORS["sidebar"], fg="#72798C").pack(anchor="w", padx=20, pady=(4, 16))

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.container = ttk.Frame(right)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)
        bar = tk.Frame(right, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)
        bar.grid(row=1, column=0, sticky="ew")
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(side="left", padx=14, pady=5)
        self.app_update_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.app_update_var, style="Status.TLabel").pack(side="right", padx=14)

    def _add_nav(self, page, glyph, key, hint):
        item = SidebarItem(self.sidebar, glyph, lambda p=page: self.show(p), binder=self.b, key=key, text=MODULE_NAMES.get(page, ""), hint_key=hint)
        item.pack(fill="x", padx=12, pady=2)
        self.nav_items[page] = item

    def _paint_lang_switch(self):
        for lang, lb in self.lang_buttons.items():
            if lang == self.tr.lang:
                lb.configure(bg="#FFFFFF", fg="#111111")
            else:
                lb.configure(bg=COLORS["sidebar_hover"], fg=COLORS["sidebar_muted"])

    def _build_pages(self):
        from pkt.ui.pages.analyze import AnalyzePage
        from pkt.ui.pages.data import DataPage
        from pkt.ui.pages.home import HomePage
        from pkt.ui.pages.settings import SettingsPage
        from pkt.ui.pages.train import TrainPage
        self.pages["home"] = HomePage(self.container, self)
        self.pages["data"] = DataPage(self.container, self)
        self.pages["train"] = TrainPage(self.container, self)
        self.pages["analyze"] = AnalyzePage(self.container, self)
        self.pages["settings"] = SettingsPage(self.container, self)
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _build_translator(self):
        """The language switch for the embedded programs: catalogs per target language, swept over their pages (pkt/ui/xlate.py)."""
        from pkt.ui import xlate
        from pkt.ui.lang import analyze_en, data_th
        self.xl = xlate.Translator(self.root, lambda: self.tr.lang, [xlate.Catalog("th", data_th.EXACT, data_th.TEMPLATES),
                                                                   xlate.Catalog("en", analyze_en.EXACT, analyze_en.TEMPLATES, fragments=True)])
        self.xl.areas = [self.pages["data"], self.pages["analyze"]]
        self.xl.install()

    def show(self, name):
        if name not in self.pages:
            return None
        self.current = name
        for key, page in self.pages.items():
            if key == name:
                page.grid()
                page.tkraise()
            else:
                page.grid_remove()                  # a hidden page is really unmapped (the PKT Data tabs listen to key presses only while mapped)
        for key, item in self.nav_items.items():
            item.set_active(key == name)
        on_show = getattr(self.pages[name], "on_show", None)
        if on_show:
            on_show()
        return self.pages[name]

    # ================================================================ module data
    def info_of(self, mid):
        mod_def = next(d for d in self.defs if d["id"] == mid)
        return mod_def, resolve_module(mod_def, self.settings, self.project_root)

    def refresh_modules(self):
        """Read the version/branch of every module from git again and tell the pages."""
        for mod_def in self.defs:
            info = resolve_module(mod_def, self.settings, self.project_root)
            self.versions[mod_def["id"]] = read_version(info, mod_def)
        self.notify()

    def notify(self):
        for fn in list(self.refreshers):
            try:
                fn()
            except tk.TclError:
                pass
        self._show_app_update()

    # ================================================================ actions
    def _open_path(self, path):
        if os.name == "nt":
            os.startfile(path)                      # noqa: S606 (the user's own folder)
        else:
            subprocess.Popen(["xdg-open", path])

    def open_folder(self, mid):
        _d, info = self.info_of(mid)
        if not info["exists"]:
            messagebox.showerror(self.t("app_title"), self.t("module_missing", name=info["name"], path=info["folder"]), parent=self.root)
            return False
        self._open_path(info["folder"])
        return True

    def launch(self, mid):
        """PKT Train is a page of this app; the other modules start as their own program (their own window). Returns the Popen / the page / None."""
        mod_def, info = self.info_of(mid)
        name = info["name"]
        if not info["exists"]:
            messagebox.showerror(self.t("app_title"), self.t("module_missing", name=name, path=info["folder"]), parent=self.root)
            return None
        if not info["launchable"]:
            return None
        if mod_def.get("page") in self.pages:
            return self.show(mod_def["page"])
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
        self.set_status("opened", name=name)
        self.root.after(EARLY_EXIT_CHECK_MS, lambda: self._check_early_exit(mid, name, proc, log_path))
        return proc

    def _check_early_exit(self, mid, name, proc, log_path):
        code = proc.poll()
        if code is not None and code != 0:
            messagebox.showerror(self.t("app_title"), self.t("exited_early", name=name, code=code, log=log_path), parent=self.root)

    def create_shortcut(self):
        ok, result = shortcut.create_shortcut(self.project_root)
        if ok:
            self.set_status("shortcut_done", path=result)
        else:
            messagebox.showerror(self.t("app_title"), self.t("shortcut_fail", msg=result), parent=self.root)
        return ok

    def save_modules_settings(self, folders, pythons, auto_check):
        """Keep only what differs from modules.json (a folder or a Python command the user typed)."""
        mods = {}
        for mod_def in self.defs:
            mid = mod_def["id"]
            default_folder = resolve_module(mod_def, {}, self.project_root)["folder"]
            entry = {}
            folder = os.path.normpath(folders.get(mid, "").strip()) if folders.get(mid, "").strip() else ""
            if folder and folder != default_folder:
                entry["path"] = folder
            if pythons.get(mid, "").strip():
                entry["python"] = pythons[mid].strip()
            if entry:
                mods[mid] = entry
        self.settings["modules"] = mods
        self.settings["auto_check_updates"] = bool(auto_check)
        self._save()
        self.set_status("saved")
        self.refresh_modules()

    def set_analyze_model(self, path):
        ok = shared.set_analyze_model(self.settings, path)
        self._save()
        self.notify()
        return ok

    # ================================================================ updates (git)
    def _update_targets(self):
        out = []
        for mod_def in self.defs:
            info = resolve_module(mod_def, self.settings, self.project_root)
            if info["exists"] and updates.own_repo(info["folder"]):          # normally the modules are part of this repo: one "app" update covers them
                out.append((mod_def["id"], info["folder"]))
        out.append(("app", self.project_root))
        return out

    def check_updates(self):
        """Look on GitHub for new commits of every module and of this app (in a thread; the results are drawn by _poll_updates)."""
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
            if not self.root.winfo_exists():
                return
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
                    name = self.name_of(mid)
                    if ok:
                        self.status_var.set(self.t("updates_done", name=name) + (" — " + self.t("updates_restart") if mid == "app" else ""))
                        self.updates[mid] = updates.check_repo(self.folder_of(mid), fetch=False)
                        self.refresh_modules()
                    else:
                        messagebox.showerror(self.t("app_title"), self.t("updates_failed", name=name, msg=msg), parent=self.root)
                    changed = True
        except queue.Empty:
            pass
        if changed:
            self.notify()
        self.root.after(300, self._poll_updates)

    def folder_of(self, mid):
        return self.project_root if mid == "app" else self.info_of(mid)[1]["folder"]

    def update_text(self, res):
        """(text, colour kind) of an update-check result; kind is ok / warn / bad / neutral."""
        st = res["state"]
        if st == "uptodate":
            text, kind = self.t("updates_uptodate"), "ok"
        elif st == "behind":
            text, kind = self.t("updates_behind", n=res["behind"]), "warn"
        elif st == "ahead":
            text, kind = self.t("updates_ahead", n=res["ahead"]), "neutral"
        elif st == "diverged":
            text, kind = self.t("updates_diverged", ahead=res["ahead"], behind=res["behind"]), "bad"
        elif st == "no_git":
            text, kind = self.t("updates_no_git"), "neutral"
        else:
            text, kind = self.t("updates_no_upstream"), "neutral"
        if st in ("uptodate", "behind", "ahead", "diverged") and res.get("error"):
            text += " · " + self.t("updates_offline")
        return text, kind

    def _show_app_update(self):
        res = self.updates.get("app")
        if self.checking and res is None:
            self.app_update_var.set(self.t("updates_checking"))
            return
        if res is None or res["state"] == "missing":
            self.app_update_var.set("")
        else:
            self.app_update_var.set(f"{self.t('app_self')}: {self.update_text(res)[0]}")

    def update_module(self, mid):
        """Take the new commits of a module (or this app) with a fast-forward pull, after the user confirms."""
        res = self.updates.get(mid)
        if not res or res["state"] != "behind":
            return False
        folder = self.folder_of(mid)
        name = self.name_of(mid)
        log = chr(10).join(updates.incoming(folder)) or "-"
        if not messagebox.askyesno(self.t("app_title"), self.t("updates_confirm", name=name, log=log), parent=self.root):
            return False
        self.set_status("updates_checking")
        threading.Thread(target=lambda: self.update_q.put(("pulled", mid, updates.pull_ff(folder))), daemon=True).start()
        return True


def main():
    import ctypes
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)        # crisp text on high-DPI screens (before Tk starts)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    PKTApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
