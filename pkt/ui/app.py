"""PK Transport main window: a navigation rail on the left, one page at a time on the right (Home, the modules, Modules, Settings).

This is the shell. PKT Data, PKT Train and PKT Analyze are modules: separate repositories that are installed into modules/<id> from the
Modules page (pkt/modman.py) and appear as pages through their plugin file (pkt/plugin.py). The shell keeps the language, the settings,
the update checks and the module operations; the pages only draw and call these methods (the plugin API of the modules)."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from pkt import __version__, envsetup, modman, plugin, shared, shortcut, updates
from pkt.i18n import LANGS, LANG_NAMES, Translator
from pkt.modules import DEFAULT_MODULES_FILE, ROOT, SETTINGS_FILE, load_settings, python_command, save_settings
from pkt.ui import theme
from pkt.ui.bind import TextBinder
from pkt.ui.kit import SidebarItem
from pkt.ui.theme import COLORS, F

LOG_DIR = os.path.join(ROOT, "logs")
NAV_GLYPHS = {"home": "⌂", "data": "▣", "train": "◈", "analyze": "◫", "modules": "⇩", "settings": "⚙"}
NAV_TEXT = {"home": "nav_home", "modules": "nav_modules", "settings": "nav_settings"}
NAV_HINT = {"home": "nav_hint_home", "data": "nav_hint_data", "train": "nav_hint_train", "analyze": "nav_hint_analyze",
            "modules": "nav_hint_modules", "settings": "nav_hint_settings"}


class PKTApp:
    def __init__(self, root, settings_path=SETTINGS_FILE, defs_path=DEFAULT_MODULES_FILE, project_root=ROOT, github=None):
        self.root = root
        self.settings_path = settings_path
        self.project_root = project_root
        self.github = {"api_base": modman.API_BASE, "zip_url": modman.ZIP_URL, "raw_url": updates.RAW_URL, "app_zip_url": updates.ZIP_URL}
        self.github.update(github or {})                 # (the tests point these at a local web server)
        self.defs = modman.load_registry(defs_path)
        self.module_ids = [d["id"] for d in self.defs]
        self.settings = load_settings(settings_path)
        self.tr = Translator(self.settings.get("language", "th"))
        self.b = TextBinder(self.tr)
        self.status_var = tk.StringVar(value="")
        self.lang_var = tk.StringVar(value=self.tr.lang)
        self.mod_state = {}             # module id -> modman.installed_state(...)
        self.tags = {}                  # module id -> released versions (newest first), from GitHub
        self.tag_errors = {}            # module id -> why the versions could not be read
        self.plugins = {}               # module id -> the imported plugin module
        self.plugin_errors = {}         # module id -> why the plugin could not be loaded
        self._plugin_catalogs = {}      # module id -> the xlate catalogs it registered
        self.mod_busy = set()           # module ids with an install / update / uninstall running
        self.mod_log = []               # lines of the module operations (shown on the Modules page)
        self.restart_needed = set()     # modules whose files changed while their page is open
        self._queue_after = []          # module ids still to install after the current one (install missing / update all)
        self.updates = {}               # module id (or 'app') -> {'state': 'behind' | 'uptodate' ...}
        self.checking = False
        self.update_q = queue.Queue()   # results of the threads (Tk is only touched from the main thread)
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
        self._build_translator()
        self._build_pages()
        self.refresh_modules()
        self.show("home")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(300, self._poll_updates)
        if self.settings.get("auto_check_updates", True):
            self.check_updates(force=False)

    # ================================================================ closing
    def hosts(self):
        return [self.pages[m] for m in self.module_ids if m in self.pages]

    def on_close(self):
        """Close the window; a module that is still working (a training, an analysis) is stopped after the user confirms."""
        busy = [h for h in self.hosts() if h.is_running()]
        if busy:
            names = ", ".join(self.name_of(h.mid) for h in busy)
            if not messagebox.askyesno(self.t("app_title"), self.t("module_busy_close", name=names), parent=self.root):
                return
            for h in busy:
                h.stop_for_exit()
            self.root.after(800, self.root.destroy)             # a run ends after its current frame
            return
        self.root.destroy()

    # ================================================================ texts / language / settings
    def t(self, key, **kw):
        return self.tr.t(key, **kw)

    def name_of(self, mid):
        if mid == "app":
            return self.t("app_self")
        return next((d["name"] for d in self.defs if d["id"] == mid), mid)

    def set_language(self, lang):
        if lang not in LANGS:
            return
        self.tr.set_lang(lang)
        self.lang_var.set(lang)
        self.settings["language"] = lang
        self.save_settings()
        self.root.title(f"PK Transport {__version__}")
        self._paint_lang_switch()
        self.b.refresh()
        self._show_app_update()
        self.xl.sweep(full=True)                          # the texts of the modules that were written in one language (every tab, shown or not)

    def save_settings(self):
        try:
            save_settings(self.settings, self.settings_path)
        except OSError:
            pass

    _save = save_settings                                 # (the old name)

    def set_status(self, key=None, **kw):
        self.status_var.set(self.t(key, **kw) if key else "")

    # ---------------------------------------------------------------- the API the module pages use
    def user_data_dir(self, *parts):
        """A folder for what the user makes (trained runs, results ...): outside the modules, so install / update / uninstall never touch it."""
        return modman.user_data_dir(self.project_root, *parts)

    def open_path(self, path):
        if os.name == "nt":
            os.startfile(path)                      # noqa: S606 (the user's own folder)
        else:
            subprocess.Popen(["xdg-open", path])

    _open_path = open_path

    def python_for(self, mid):
        """The command (list) that starts a Python for the module: its override in the settings, else this Python."""
        return python_command((((self.settings.get("modules") or {}).get(mid) or {}).get("python", "")))

    def set_analyze_model(self, path):
        ok = shared.set_analyze_model(self.settings, path)
        self.save_settings()
        self.notify()
        return ok

    def get_analyze_model(self):
        return shared.get_analyze_model(self.settings)

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
        for page in ["home"] + self.module_ids + ["modules"]:
            self._add_nav(page)
        tk.Frame(self.sidebar, bg=COLORS["sidebar"]).pack(fill="both", expand=True)
        self._add_nav("settings")
        tk.Frame(self.sidebar, bg=COLORS["sidebar_line"], height=1).pack(fill="x", padx=18, pady=(12, 12))
        lang_row = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        lang_row.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(lang_row, text="◎", font=("Segoe UI Symbol", 12), bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"]).pack(side="left", padx=(0, 8))
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

    def _add_nav(self, page):
        is_module = page in self.module_ids
        item = SidebarItem(self.sidebar, NAV_GLYPHS.get(page, "▣"), lambda p=page: self.show(p), binder=self.b, key=NAV_TEXT.get(page),
                           text=self.name_of(page) if is_module else "", hint_key=NAV_HINT.get(page, "nav_hint_home"))
        item.pack(fill="x", padx=12, pady=2)
        self.nav_items[page] = item

    def _paint_lang_switch(self):
        for lang, lb in self.lang_buttons.items():
            if lang == self.tr.lang:
                lb.configure(bg="#FFFFFF", fg="#111111")
            else:
                lb.configure(bg=COLORS["sidebar_hover"], fg=COLORS["sidebar_muted"])

    def _build_pages(self):
        from pkt.ui.pages.home import HomePage
        from pkt.ui.pages.host import ModuleHost
        from pkt.ui.pages.modules import ModulesPage
        from pkt.ui.pages.settings import SettingsPage
        self.pages["home"] = HomePage(self.container, self)
        for mid in self.module_ids:
            self.pages[mid] = ModuleHost(self.container, self, mid)
        self.pages["modules"] = ModulesPage(self.container, self)
        self.pages["settings"] = SettingsPage(self.container, self)
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _build_translator(self):
        """The language switch for modules written in one language: catalogs per target language, swept over their pages (pkt/ui/xlate.py)."""
        from pkt.ui import xlate
        self.xl = xlate.Translator(self.root, lambda: self.tr.lang, [])
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
    def mod_def(self, mid):
        return next(d for d in self.defs if d["id"] == mid)

    def state_of(self, mid):
        return self.mod_state.get(mid) or modman.installed_state(self.project_root, self.mod_def(mid), self.settings)

    def module_ready(self, mid):
        st = self.state_of(mid)
        return bool(st["installed"] and not st["problem"])

    def refresh_modules(self):
        """Read which modules are installed (and their versions) again and tell the pages."""
        for d in self.defs:
            self.mod_state[d["id"]] = modman.installed_state(self.project_root, d, self.settings)
        self._module_updates()
        self.notify()

    def _module_updates(self):
        for d in self.defs:
            mid = d["id"]
            st, tags = self.mod_state[mid], self.tags.get(mid)
            verdict = modman.update_state(st, tags) if tags else ""
            if verdict:
                self.updates[mid] = {"state": "behind" if verdict == "update" else "uptodate", "zip": True, "local": st["version"], "remote": tags[0]["version"],
                                     "behind": 1 if verdict == "update" else 0, "ahead": 0, "error": ""}
            else:
                self.updates.pop(mid, None)

    def notify(self):
        for fn in list(self.refreshers):
            try:
                fn()
            except tk.TclError:
                pass
        self._show_app_update()

    # ================================================================ plugins
    def plugin_of(self, mid):
        """The imported plugin module of an installed module (None, with plugin_errors[mid] set, when it cannot be used)."""
        if mid in self.plugins:
            return self.plugins[mid]
        st = self.state_of(mid)
        if not st["installed"]:
            return None
        if st["problem"]:
            self.plugin_errors[mid] = st["problem"]
            return None
        os.environ["PKT_USER_DATA"] = self.user_data_dir(st["manifest"].get("name", mid).replace(" ", "-"))      # the modules keep their own files here
        try:
            mod = plugin.load_plugin(st["folder"], mid, st["manifest"])
        except plugin.PluginError as exc:
            self.plugin_errors[mid] = str(exc)
            return None
        self.plugin_errors.pop(mid, None)
        self.plugins[mid] = mod
        self._register_plugin(mid, mod)
        return mod

    def _register_plugin(self, mid, mod):
        from pkt.ui import xlate
        try:
            extra = mod.texts() if hasattr(mod, "texts") else {}
            if extra:
                self.tr.add_texts(extra)
            cats = [xlate.Catalog(c["lang"], c.get("exact"), c.get("templates"), fragments=c.get("fragments", False)) for c in (mod.catalogs() if hasattr(mod, "catalogs") else [])]
        except Exception as exc:                                    # a module with a broken texts()/catalogs() must not break the window
            self.plugin_errors[mid] = f"{type(exc).__name__}: {exc}"
            return
        self._plugin_catalogs[mid] = cats
        self.xl.catalogs.extend(cats)

    def forget_plugin(self, mid):
        """After the files of a module changed: drop what was imported from it so the new version loads (only when its page was never created)."""
        for cat in self._plugin_catalogs.pop(mid, []):
            if cat in self.xl.catalogs:
                self.xl.catalogs.remove(cat)
        self.plugins.pop(mid, None)
        self.plugin_errors.pop(mid, None)
        plugin.purge(self.state_of(mid)["folder"], mid)

    def page_created(self, mid):
        host = self.pages.get(mid)
        return bool(host is not None and getattr(host, "page", None) is not None)

    # ================================================================ module operations (threads; results come through update_q)
    def _log(self, mid, text):
        self.update_q.put(("modlog", mid, text))

    def install_module(self, mid, tag=None):
        """Install a module (the newest version, or `tag`) / switch it to another version, then its libraries. Returns False when busy."""
        if self.mod_busy:
            messagebox.showinfo(self.t("app_title"), self.t("mod_busy"), parent=self.root)
            return False
        d = self.mod_def(mid)
        if self.state_of(mid)["linked"]:
            messagebox.showinfo(self.t("app_title"), self.t("mod_linked_note", name=d["name"]), parent=self.root)
            return False
        self.mod_busy.add(mid)
        self.notify()
        github = dict(self.github)
        root, settings = self.project_root, dict(self.settings)
        cache = self.user_data_dir("cache")

        def work():
            try:
                pick = tag
                if pick is None:
                    tags = modman.list_tags(d, api_base=github["api_base"], cache_dir=cache)
                    if not tags:
                        raise modman.ModManError("no released version was found on GitHub")
                    pick = tags[0]["tag"]
                manifest = modman.install(root, d, pick, log=lambda m: self._log(mid, m), zip_url=github["zip_url"])
                folder = modman.module_folder(root, d, settings)[0]
                envsetup.prepare_module(manifest, folder, log=lambda m: self._log(mid, m))
                self.update_q.put(("moddone", mid, (True, manifest["version"])))
            except Exception as exc:                                 # a failed download / pip is shown to the user, never a crash
                self.update_q.put(("moddone", mid, (False, str(exc))))

        threading.Thread(target=work, daemon=True).start()
        return True

    def uninstall_module(self, mid):
        d = self.mod_def(mid)
        st = self.state_of(mid)
        if st["linked"]:
            messagebox.showinfo(self.t("app_title"), self.t("mod_linked_note", name=d["name"]), parent=self.root)
            return False
        if self.mod_busy or not st["installed"]:
            return False
        if not messagebox.askyesno(self.t("app_title"), self.t("mod_confirm_uninstall", name=d["name"]), parent=self.root):
            return False
        created = self.page_created(mid)
        try:
            modman.uninstall(self.project_root, d, log=lambda m: self.mod_log.append(m))
        except modman.ModManError as exc:
            messagebox.showerror(self.t("app_title"), self.t("mod_failed", name=d["name"], msg=str(exc)), parent=self.root)
            return False
        if created:
            self.restart_needed.add(mid)
        else:
            self.forget_plugin(mid)
        self.updates.pop(mid, None)
        self.set_status("mod_removed", name=d["name"])
        self.refresh_modules()
        return True

    def update_all(self):
        """Update every installed module that has a newer version (one after the other)."""
        todo = [d["id"] for d in self.defs if self.updates.get(d["id"], {}).get("state") == "behind" and not self.state_of(d["id"])["linked"]]
        if not todo:
            self.set_status("mod_all_uptodate")
            return False
        self._queue_after = todo[1:]
        return self.install_module(todo[0])

    def install_missing(self):
        todo = [d["id"] for d in self.defs if not self.state_of(d["id"])["installed"]]
        if not todo:
            return False
        self._queue_after = todo[1:]
        return self.install_module(todo[0])

    def fetch_tags(self, ids=None):
        """Read the released versions of the modules from GitHub (in a thread)."""
        ids = ids or self.module_ids
        github = self.github
        cache = self.user_data_dir("cache")

        def work():
            for mid in ids:
                try:
                    tags = modman.list_tags(self.mod_def(mid), api_base=github["api_base"], cache_dir=cache)
                    self.update_q.put(("tags", mid, (tags, "")))
                except modman.ModManError as exc:
                    self.update_q.put(("tags", mid, (None, str(exc))))

        threading.Thread(target=work, daemon=True).start()

    def restart_app(self):
        """Start PK Transport again and close this window (after a module that was open was replaced or removed)."""
        main = os.path.join(self.project_root, "main.py")
        try:
            subprocess.Popen([sys.executable, main], cwd=self.project_root)
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.root)
            return False
        self.root.destroy()
        return True

    # ================================================================ shortcut / settings of the modules
    def create_shortcut(self):
        ok, result = shortcut.create_shortcut(self.project_root)
        if ok:
            self.set_status("shortcut_done", path=result)
        else:
            messagebox.showerror(self.t("app_title"), self.t("shortcut_fail", msg=result), parent=self.root)
        return ok

    def save_modules_settings(self, folders, pythons, auto_check):
        """Keep only what differs from the defaults: a linked development folder (instead of modules/<id>) and a Python command."""
        mods = {}
        for d in self.defs:
            mid = d["id"]
            default_folder = modman.module_folder(self.project_root, d, {})[0]
            entry = {}
            folder = os.path.normpath(folders.get(mid, "").strip()) if folders.get(mid, "").strip() else ""
            if folder and folder != os.path.normpath(default_folder):
                entry["path"] = folder
            if pythons.get(mid, "").strip():
                entry["python"] = pythons[mid].strip()
            if entry:
                mods[mid] = entry
        self.settings["modules"] = mods
        self.settings["auto_check_updates"] = bool(auto_check)
        self.save_settings()
        self.set_status("saved")
        self.refresh_modules()

    # ================================================================ updates
    def check_updates(self, force=True):
        """Look on GitHub for a newer version of this app and of every installed module (in a thread; _poll_updates draws the results).
        The list of versions of a module is kept for an hour; the button asks again (force), the check at start-up may use the kept list."""
        if self.checking:
            return False
        self.checking = True
        self.app_update_var.set(self.t("updates_checking"))
        folder = self.project_root
        github = self.github
        cache = self.user_data_dir("cache")

        def work():
            if updates.own_repo(folder):
                self.update_q.put(("check", "app", updates.check_repo(folder)))
            else:                                                       # a "Download ZIP" folder: compare the version number instead of git
                self.update_q.put(("check", "app", updates.check_zip(folder, raw_url=github["raw_url"])))
            for mid in self.module_ids:
                try:
                    tags = modman.list_tags(self.mod_def(mid), api_base=github["api_base"], cache_dir=cache, ttl=0 if force else modman.TAG_CACHE_SECONDS)
                    self.update_q.put(("tags", mid, (tags, "")))
                except modman.ModManError as exc:
                    self.update_q.put(("tags", mid, (None, str(exc))))
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
                elif kind == "tags":
                    tags, err = data
                    if tags is not None:
                        self.tags[mid] = tags
                        self.tag_errors.pop(mid, None)
                    else:
                        self.tag_errors[mid] = err
                    self._module_updates()
                    changed = True
                elif kind == "modlog":
                    self.mod_log.append(data)
                    self.status_var.set(data[:120])
                    changed = True
                elif kind == "moddone":
                    self._module_done(mid, *data)
                    changed = True
                elif kind == "pulled":                                  # this app was updated (git pull / zip)
                    ok, msg = data
                    name = self.name_of(mid)
                    if ok:
                        self.status_var.set(self.t("updates_done", name=name) + " — " + self.t("updates_restart"))
                        folder = self.project_root
                        self.updates[mid] = updates.check_repo(folder, fetch=False) if updates.own_repo(folder) else updates.check_zip(folder, raw_url=self.github["raw_url"])
                    else:
                        messagebox.showerror(self.t("app_title"), self.t("updates_failed", name=name, msg=msg), parent=self.root)
                    changed = True
        except queue.Empty:
            pass
        if changed:
            self.notify()
        self.root.after(300, self._poll_updates)

    def _module_done(self, mid, ok, msg):
        name = self.name_of(mid)
        created = self.page_created(mid)
        self.mod_busy.discard(mid)
        if ok:
            self.mod_log.append(self.t("mod_installed_ok", name=name, version=msg))
            self.status_var.set(self.t("mod_installed_ok", name=name, version=msg))
            if created:
                self.restart_needed.add(mid)
            else:
                self.forget_plugin(mid)
            self.refresh_modules()
            self.fetch_tags([mid])                                        # the update state of this module
            if self._queue_after:
                nxt = self._queue_after.pop(0)
                self.root.after(100, lambda: self.install_module(nxt))
            elif created:
                if messagebox.askyesno(self.t("app_title"), self.t("mod_restart_needed", name=name), parent=self.root):
                    self.restart_app()
        else:
            self.mod_log.append(self.t("mod_failed", name=name, msg=msg))
            self._queue_after = []
            messagebox.showerror(self.t("app_title"), self.t("mod_failed", name=name, msg=msg), parent=self.root)
            self.refresh_modules()

    def update_text(self, res):
        """(text, colour kind) of an update-check result; kind is ok / warn / bad / neutral."""
        st = res["state"]
        if st == "uptodate":
            text, kind = self.t("updates_uptodate"), "ok"
        elif st == "behind" and res.get("zip"):
            text, kind = self.t("updates_new_version", new=res["remote"], old=res["local"]), "warn"
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
        """Update a module (download the newest version) or this app (git pull / zip), after the user confirms."""
        if mid != "app":
            res = self.updates.get(mid)
            if not res or res["state"] != "behind":
                return False
            return self.install_module(mid)
        res = self.updates.get("app")
        if not res or res["state"] != "behind":
            return False
        folder = self.project_root
        name = self.name_of("app")
        if res.get("zip"):                                                  # no git here: download the zip of the new version
            if not messagebox.askyesno(self.t("app_title"), self.t("updates_confirm_zip", name=name, new=res["remote"], old=res["local"]), parent=self.root):
                return False
            self.set_status("updates_checking")
            zip_url = self.github["app_zip_url"]
            threading.Thread(target=lambda: self.update_q.put(("pulled", mid, updates.apply_zip(folder, zip_url=zip_url))), daemon=True).start()
            return True
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
