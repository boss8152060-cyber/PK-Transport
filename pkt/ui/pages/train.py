"""PKT Train page: choose a model and size, train on this PC (live log, stop, resume) or copy the code for Colab, hand a trained model to PKT Analyze."""
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from pkt import shared
from pkt import train_core as TC
from pkt.modules import python_command
from pkt.ui.kit import Card, ScrollFrame, autowrap, page_header
from pkt.ui.theme import COLORS, F

COLAB_URL = "https://colab.research.google.com/"
POLL_MS = 150


class TrainPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.root = app.root
        self.b = app.b
        self.proc = None
        self.reader = None
        self.log_q = queue.Queue()
        self.env_q = queue.Queue()
        self.env_info = None
        self.run_info = {}
        saved = (app.settings.get("train") or {})
        self.family_var = tk.StringVar(value=saved.get("family") if saved.get("family") in TC.FAMILIES else "yolo26")
        self.size_var = tk.StringVar(value="")
        self.where_var = tk.StringVar(value=saved.get("where", "local"))
        self.dataset_var = tk.StringVar(value=saved.get("dataset", ""))
        self.store_var = tk.StringVar(value=saved.get("store", ""))
        self.num_vars = {k: tk.StringVar(value="") for k in TC.NUMERIC_KEYS}
        self.mode_var = tk.StringVar(value="auto")
        self.source_var = tk.StringVar(value="")
        self.param_vars = {}                      # the other "# @param" fields of the script (key -> Tk variable)
        self.param_specs = []
        self.copy_var = tk.StringVar(value="")
        self.env_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value="")
        self.widgets = {}
        self.runs = []
        self.copy_options, self.copy_labels = [], []
        self.status_var = app.status_var            # one status line for the whole window
        self._build()
        self.on_family_changed(initial=True)
        self.refresh_runs()
        self.check_environment()
        app.b.on_change(self._on_language)
        app.refreshers.append(self._show_current_model)
        self.after(POLL_MS, self._poll)

    # ---------------------------------------------------------------- helpers
    def t(self, key, **kw):
        return self.app.t(key, **kw)

    @property
    def train_dir(self):
        return self.app.info_of("train")[1]["folder"]

    # ---------------------------------------------------------------- layout
    def _build(self):
        b = self.b
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = ttk.Frame(scroll.body, padding=(30, 26, 30, 30))
        body.pack(fill="both", expand=True)
        self.body = body

        head = page_header(body, b, "train_title", "train_page_sub")
        head.pack(fill="x")
        ttk.Label(body, textvariable=self.env_var, style="Muted.TLabel").pack(anchor="w", pady=(6, 14))

        # ---- model + where
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        c = card.inner
        row = ttk.Frame(c, style="Card.TFrame")
        row.pack(fill="x")
        b.label(row, "train_family", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w")
        b.label(row, "train_size", style="CardMuted.TLabel").grid(row=0, column=1, sticky="w", padx=(16, 0))
        b.label(row, "train_where", style="CardMuted.TLabel").grid(row=0, column=2, sticky="w", padx=(24, 0))
        fam = ttk.Combobox(row, textvariable=self.family_var, values=TC.FAMILY_ORDER, state="readonly", width=16)
        fam.grid(row=1, column=0, sticky="w", pady=(4, 0))
        fam.bind("<<ComboboxSelected>>", lambda e: self.on_family_changed())
        self.widgets["family"] = fam
        size = ttk.Combobox(row, textvariable=self.size_var, values=[], state="readonly", width=8)
        size.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(4, 0))
        self.widgets["size"] = size
        wf = ttk.Frame(row, style="Card.TFrame")
        wf.grid(row=1, column=2, sticky="w", padx=(24, 0), pady=(4, 0))
        b.radio(wf, "train_local", self.where_var, "local", command=self._on_where).pack(side="left")
        b.radio(wf, "train_colab", self.where_var, "colab", command=self._on_where).pack(side="left", padx=(14, 0))

        # ---- settings
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        c = card.inner
        b.label(c, "train_settings", style="CardTitle.TLabel").pack(anchor="w")
        grid = ttk.Frame(c, style="Card.TFrame")
        grid.pack(fill="x", pady=(10, 0))
        for i, key in enumerate(TC.NUMERIC_KEYS):
            b.label(grid, f"train_{key}", style="CardMuted.TLabel").grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else 12, 0))
            ttk.Entry(grid, textvariable=self.num_vars[key], width=9).grid(row=1, column=i, sticky="w", padx=(0 if i == 0 else 12, 0), pady=(4, 0))
        b.label(grid, "train_run_mode", style="CardMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(12, 0))
        b.label(grid, "train_source_run", style="CardMuted.TLabel").grid(row=2, column=3, sticky="w", padx=(12, 0), pady=(12, 0))
        mode = ttk.Combobox(grid, textvariable=self.mode_var, values=TC.TRAINING_MODES, state="readonly", width=20)
        mode.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.widgets["mode"] = mode
        ttk.Entry(grid, textvariable=self.source_var, width=14).grid(row=3, column=3, columnspan=2, sticky="w", padx=(12, 0), pady=(4, 0))

        # ---- every other Colab form field of the chosen script (optimizer, cache, augmentation ...)
        card = Card(body)
        card.pack(fill="x", pady=(0, 14))
        b.label(card.inner, "train_advanced", style="CardTitle.TLabel").pack(anchor="w")
        autowrap(b.label(card.inner, "train_advanced_hint", style="CardSubtle.TLabel", justify="left"), card.inner).pack(anchor="w", pady=(4, 0))
        self.adv_grid = ttk.Frame(card.inner, style="Card.TFrame")
        self.adv_grid.pack(fill="x", pady=(10, 0))
        for col in range(3):
            self.adv_grid.columnconfigure(col, weight=1, uniform="adv")

        # ---- local training
        self.local_frame = ttk.Frame(body)
        self.local_frame.pack(fill="x")
        lf = self.local_frame
        card = Card(lf)
        card.pack(fill="x", pady=(0, 14))
        c = card.inner
        c.columnconfigure(1, weight=1)
        b.label(c, "train_dataset", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Entry(c, textvariable=self.dataset_var).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        b.button(c, "browse", lambda: self._browse(self.dataset_var)).grid(row=1, column=2)
        b.label(c, "train_store", style="CardMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 2))
        ttk.Entry(c, textvariable=self.store_var).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        b.button(c, "browse", lambda: self._browse(self.store_var)).grid(row=3, column=2)
        bar = ttk.Frame(c, style="Card.TFrame")
        bar.grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 0))
        self.start_btn = b.button(bar, "train_start", self.start_training, style="Accent.TButton")
        self.start_btn.pack(side="left")
        self.stop_btn = b.button(bar, "train_stop", self.request_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.kill_btn = b.button(bar, "train_kill", self.kill_now, style="Danger.TButton", state="disabled")
        self.kill_btn.pack(side="left")
        b.button(bar, "train_open_results", self.open_results).pack(side="left", padx=(22, 8))
        b.button(bar, "train_open_scripts", self.open_scripts).pack(side="left")
        ttk.Label(c, textvariable=self.progress_var, style="CardOk.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.progressbar = ttk.Progressbar(c, mode="determinate", maximum=100, style="Horizontal.TProgressbar")
        self.progressbar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        # ---- trained runs
        card = Card(lf)
        card.pack(fill="x", pady=(0, 14))
        c = card.inner
        b.label(c, "train_runs", style="CardTitle.TLabel").pack(anchor="w")
        cols = ("run", "model", "best_epoch", "map50", "map50_95", "usable")
        self.col_keys = {"run": "col_run", "model": "col_model", "best_epoch": "col_best_epoch", "map50": "col_map50", "map50_95": "col_map50_95", "usable": "col_usable"}
        tf = ttk.Frame(c, style="Card.TFrame")
        tf.pack(fill="x", pady=(8, 0))
        tf.columnconfigure(0, weight=1)
        self.runs_tree = ttk.Treeview(tf, columns=cols, show="headings", height=5, selectmode="browse")
        for col in cols:
            self.runs_tree.column(col, width=(170 if col == "model" else 110), anchor="w" if col in ("model", "run") else "center")
        self.runs_tree.grid(row=0, column=0, sticky="ew")
        sb = ttk.Scrollbar(tf, command=self.runs_tree.yview)
        self.runs_tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self._heading_texts()
        rb = ttk.Frame(c, style="Card.TFrame")
        rb.pack(fill="x", pady=(10, 0))
        b.button(rb, "train_refresh", self.refresh_runs).pack(side="left")
        b.button(rb, "train_use_in_analyze", self.use_in_analyze, style="Primary.TButton").pack(side="left", padx=8)
        b.button(rb, "train_open_run", self.open_run).pack(side="left")
        ttk.Label(rb, textvariable=self.model_var, style="CardMuted.TLabel").pack(side="left", padx=(18, 0))

        # ---- log
        card = Card(lf)
        card.pack(fill="both", expand=True)
        c = card.inner
        b.label(c, "train_log", style="CardTitle.TLabel").pack(anchor="w")
        lg = ttk.Frame(c, style="Card.TFrame")
        lg.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(lg, height=13, wrap="none", state="disabled", font=("Consolas", 9), bg="#0F1626", fg="#D6DEEB", insertbackground="#D6DEEB",
                           relief="flat", highlightthickness=0, padx=10, pady=8)
        lsb = ttk.Scrollbar(lg, command=self.log.yview)
        self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")

        # ---- Colab
        self.colab_frame = ttk.Frame(body)
        card = Card(self.colab_frame)
        card.pack(fill="x")
        c = card.inner
        b.label(c, "train_colab_title", style="CardTitle.TLabel").pack(anchor="w")
        autowrap(b.label(c, "train_colab_help", style="CardMuted.TLabel", justify="left"), c).pack(anchor="w", pady=(6, 12))
        row = ttk.Frame(c, style="Card.TFrame")
        row.pack(anchor="w")
        b.label(row, "train_copy_what", style="CardMuted.TLabel").pack(side="left")
        self.copy_combo = ttk.Combobox(row, textvariable=self.copy_var, state="readonly", width=36)
        self.copy_combo.pack(side="left", padx=8)
        b.button(row, "train_copy_btn", self.copy_colab_code, style="Primary.TButton").pack(side="left")
        b.button(row, "train_open_colab", lambda: webbrowser.open(COLAB_URL)).pack(side="left", padx=8)
        self._on_where()

    def _heading_texts(self):
        for col, key in self.col_keys.items():
            self.runs_tree.heading(col, text=self.t(key))

    def _on_language(self):
        """The window language changed: redraw what a plain text binding cannot (table headings, copy list, environment, progress)."""
        self._heading_texts()
        keep = self.copy_options[self.copy_labels.index(self.copy_combo.get())] if self.copy_combo.get() in self.copy_labels else "all"
        self._refresh_copy_options(select=keep)
        if self.env_info is not None:
            self._show_environment(self.env_info)
        else:
            self.env_var.set(self.t("train_env_checking"))
        if self.is_running():
            self._set_progress()
        self._show_current_model()

    def _on_where(self):
        if self.where_var.get() == "local":
            self.colab_frame.pack_forget()
            self.local_frame.pack(fill="x")
        else:
            self.local_frame.pack_forget()
            self.colab_frame.pack(fill="x")
        self._save_choices()

    def _browse(self, var):
        path = filedialog.askdirectory(parent=self.root, initialdir=var.get() or self.train_dir)
        if path:
            var.set(os.path.normpath(path))
            self._save_choices()

    def _save_choices(self):
        self.app.settings["train"] = {"family": self.family_var.get(), "where": self.where_var.get(),
                                      "dataset": self.dataset_var.get(), "store": self.store_var.get()}
        self.app._save()

    # ---------------------------------------------------------------- trained runs / hand-off
    def refresh_runs(self):
        """Look for trained runs again (the folder in the Runs field and its sibling families)."""
        self.runs = shared.find_runs(shared.runs_root_for(self.store_dir()))
        self.runs_tree.delete(*self.runs_tree.get_children())
        for i, r in enumerate(self.runs):
            fmt = lambda v: "" if v is None else f"{v:.3f}"
            self.runs_tree.insert("", "end", iid=str(i), values=(r["run"], r["model"] or r["family"], r["best_epoch"] if r["best_epoch"] is not None else "",
                                                                  fmt(r["map50"]), fmt(r["map50_95"]), "✓" if r["usable_in_analyze"] else "—"))
        self._show_current_model()
        return self.runs

    def _show_current_model(self):
        model = shared.get_analyze_model(self.app.settings)
        self.model_var.set(self.t("train_current_model", name=os.path.basename(model) if model else self.t("train_no_model")))

    def _selected_run(self):
        sel = self.runs_tree.selection()
        if not sel:
            messagebox.showinfo(self.t("app_title"), self.t("train_pick_run"), parent=self.root)
            return None
        return self.runs[int(sel[0])]

    def use_in_analyze(self):
        """Hand the best.pt of the selected run to PKT Analyze (it starts with this model from now on)."""
        run = self._selected_run()
        if run is None:
            return False
        if not run["usable_in_analyze"]:
            messagebox.showinfo(self.t("app_title"), self.t("train_not_usable"), parent=self.root)
            return False
        self.app.set_analyze_model(run["weights"])
        self._show_current_model()
        self.status_var.set(self.t("train_model_set", path=run["weights"]))
        return True

    def open_run(self):
        run = self._selected_run()
        if run is None:
            return False
        self.app._open_path(run["folder"])
        return True

    # ---------------------------------------------------------------- model / settings
    def script(self):
        return TC.script_path(self.train_dir, self.family_var.get())

    def on_family_changed(self, initial=False):
        fam = TC.FAMILIES[self.family_var.get()]
        self.widgets["size"].configure(values=fam["sizes"])
        if not initial or self.size_var.get() not in fam["sizes"]:
            self.size_var.set(fam["default_size"])             # another family: its own default size
        path = self.script()
        if os.path.isfile(path) and not (initial and self.num_vars["epochs"].get()):
            d = TC.read_defaults(TC.read_text(path))
            for key in TC.NUMERIC_KEYS:
                if key in d:
                    self.num_vars[key].set(str(d[key]))
            self.mode_var.set(d.get("training_mode", "auto"))
            self.source_var.set(d.get("source_run_name", ""))
            self._build_params(TC.parse_params(TC.read_text(path)))
        elif not os.path.isfile(path):
            self._build_params([])
        if not self.store_var.get() or not initial:
            self.store_var.set(TC.default_store_dir(self.train_dir, self.family_var.get()))
        self._refresh_copy_options()
        self._save_choices()

    def _build_params(self, specs):
        """One input per "# @param" field: a list for choices, a check box for True/False, a text box for numbers and text."""
        for w in self.adv_grid.winfo_children():
            w.destroy()
        self.param_vars, self.param_specs = {}, specs
        for i, spec in enumerate(specs):
            row, col = divmod(i, 3)
            cell = ttk.Frame(self.adv_grid, style="Card.TFrame")
            cell.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 10, 0), pady=(0, 10))
            key = spec["key"]
            if spec["kind"] == "bool":
                var = tk.BooleanVar(value=bool(spec["default"]))
                ttk.Checkbutton(cell, text=key, variable=var, style="Card.TCheckbutton").pack(anchor="w", pady=(14, 0))
            else:
                var = tk.StringVar(value=str(spec["default"]))
                ttk.Label(cell, text=key, style="CardMuted.TLabel").pack(anchor="w")
                if spec["kind"] == "choice":
                    ttk.Combobox(cell, textvariable=var, values=spec["options"], state="readonly").pack(fill="x", pady=(4, 0))
                else:
                    ttk.Entry(cell, textvariable=var).pack(fill="x", pady=(4, 0))
            self.param_vars[key] = var

    def _refresh_copy_options(self, select="all"):
        labels = [self.t("train_copy_all"), self.t("train_copy_file")]
        self.copy_options = ["all", "file"]
        path = self.script()
        if os.path.isfile(path):
            for n in TC.cell_numbers(TC.read_text(path)):
                labels.append(self.t("train_copy_cell", n=n))
                self.copy_options.append(f"cell{n}")
        self.copy_combo.configure(values=labels)
        self.copy_labels = labels
        self.copy_combo.set(labels[self.copy_options.index(select)] if select in self.copy_options else labels[0])

    def current_settings(self):
        s = {"model_size": self.size_var.get(), "training_mode": self.mode_var.get()}
        if self.source_var.get().strip():
            s["source_run_name"] = self.source_var.get().strip()
        for key in TC.NUMERIC_KEYS:
            v = self.num_vars[key].get().strip()
            if v:
                try:
                    s[key] = int(float(v))
                except ValueError:
                    pass
        params = {}
        for spec in self.param_specs:
            v = self.param_vars[spec["key"]].get()
            if spec["kind"] in ("int", "number") and not str(v).strip():
                continue
            params[spec["key"]] = v
        if params:
            s["params"] = params
        return s

    # ---------------------------------------------------------------- environment
    def python_cmd(self):
        return python_command(((self.app.settings.get("modules") or {}).get("train") or {}).get("python", ""))

    def check_environment(self):
        self.env_var.set(self.t("train_env_checking"))
        cmd = self.python_cmd()

        def work():
            self.env_q.put(TC.probe_environment(cmd))          # shown by _poll (Tk is only touched from the main thread)

        threading.Thread(target=work, daemon=True).start()

    def _show_environment(self, info):
        self.env_info = info
        try:
            if "error" in info or "torch_error" in info or "ultralytics_error" in info:
                err = info.get("error") or info.get("torch_error") or info.get("ultralytics_error")
                self.env_var.set(self.t("train_env_fail", error=err))
            elif info.get("cuda"):
                self.env_var.set(self.t("train_env_ok", python=info["python"], torch=info["torch"], gpu=info.get("gpu", "?"),
                                        vram=info.get("vram_gb", "?"), ultralytics=info.get("ultralytics", "?")))
            else:
                self.env_var.set(self.t("train_env_nogpu", python=info["python"], torch=info["torch"], ultralytics=info.get("ultralytics", "?")))
        except tk.TclError:
            pass

    # ---------------------------------------------------------------- Colab: copy the code
    def colab_text(self):
        """The text to copy: the script with the chosen model and settings written in, all / the whole file / one cell."""
        path = self.script()
        if not os.path.isfile(path):
            return None, None
        text, _missing = TC.patch_text(TC.read_text(path), self.current_settings())
        which = self.copy_options[self.copy_labels.index(self.copy_combo.get())] if self.copy_combo.get() in self.copy_labels else "all"
        if which == "file":
            return text, self.t("train_copy_file")
        if which == "all":
            return TC.extract_cells_from(text, 1), self.t("train_copy_all")
        n = int(which[4:])
        return TC.extract_cell(text, n), self.t("train_copy_cell", n=n)

    def copy_colab_code(self):
        text, what = self.colab_text()
        if not text:
            messagebox.showerror(self.t("app_title"), self.t("train_no_script", path=self.script()), parent=self.root)
            return False
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()                         # keep the clipboard after the window is closed (Windows)
        self.status_var.set(self.t("train_copied", what=what, lines=len(text.splitlines())))
        return True

    # ---------------------------------------------------------------- local training
    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def store_dir(self):
        return self.store_var.get().strip() or TC.default_store_dir(self.train_dir, self.family_var.get())

    def start_training(self):
        if self.is_running():
            messagebox.showinfo(self.t("app_title"), self.t("train_already_running"), parent=self.root)
            return None
        path = self.script()
        if not os.path.isfile(path):
            messagebox.showerror(self.t("app_title"), self.t("train_no_script", path=path), parent=self.root)
            return None
        family, size = self.family_var.get(), self.size_var.get()
        try:
            run_script, missing = TC.write_run_script(self.train_dir, family, self.current_settings(), time.strftime("%Y%m%d_%H%M%S"))
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.root)
            return None
        if missing:
            self._append_log(self.t("train_patch_missing", keys=", ".join(missing)) + "\n")
        store = self.store_dir()
        os.makedirs(store, exist_ok=True)
        flag = TC.stop_flag_path(store)
        if os.path.isfile(flag):
            try:
                os.remove(flag)                    # a STOP.flag left from an earlier run would stop this one at once
            except OSError:
                pass
        env = TC.build_env(family, size, self.dataset_var.get().strip(), store)
        cmd = self.python_cmd() + ["-u", run_script]
        self._append_log("$ " + " ".join(cmd) + "\n")
        try:
            self.proc = subprocess.Popen(cmd, cwd=self.train_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.root)
            return None
        self.run_info = {"family": TC.FAMILIES[family]["name"], "size": size, "store": store, "epoch": None, "total": None}
        self.reader = threading.Thread(target=self._read_output, args=(self.proc,), daemon=True)
        self.reader.start()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.kill_btn.configure(state="normal")
        self._set_progress()
        self._save_choices()
        return self.proc

    def _read_output(self, proc):
        for line in proc.stdout:
            self.log_q.put(line)
        proc.wait()
        self.log_q.put(None)                       # end marker

    def _poll(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            while True:
                self._show_environment(self.env_q.get_nowait())
        except queue.Empty:
            pass
        finished = False
        try:
            while True:
                line = self.log_q.get_nowait()
                if line is None:
                    finished = True
                    break
                self._append_log(line)
                p = TC.parse_progress(line)
                if p:
                    self.run_info["epoch"] = p[0]
                    if p[1]:
                        self.run_info["total"] = p[1]
                    self._set_progress()
        except queue.Empty:
            pass
        if finished:
            self._on_finished()
        self.after(POLL_MS, self._poll)

    def _set_progress(self):
        info = self.run_info
        prog = self.t("train_progress", epoch=info["epoch"], total=info["total"] or "?") if info.get("epoch") else ""
        self.progress_var.set(self.t("train_running", family=info.get("family", ""), size=info.get("size", ""), progress=prog))
        if info.get("epoch") and info.get("total"):
            self.progressbar.configure(value=min(100.0, 100.0 * info["epoch"] / info["total"]))

    def _on_finished(self):
        code = self.proc.returncode if self.proc else None
        self.progress_var.set("")
        self.progressbar.configure(value=0)
        self.status_var.set(self.t("train_finished", code=code))
        self.refresh_runs()                           # a new run (or new epochs) may be in the list now
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.kill_btn.configure(state="disabled")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def request_stop(self):
        """Ask the scripts to finish after the current epoch (they watch STOP.flag in the runs folder)."""
        flag = TC.stop_flag_path(self.store_dir())
        try:
            os.makedirs(os.path.dirname(flag), exist_ok=True)
            with open(flag, "w") as f:
                f.write("stop")
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.root)
            return False
        self.status_var.set(self.t("train_stopped_flag"))
        return True

    def kill_now(self):
        if self.proc is not None:
            TC.kill_process_tree(self.proc)
        return True

    def open_results(self):
        self.app._open_path(self.store_dir() if os.path.isdir(self.store_dir()) else self.train_dir)

    def open_scripts(self):
        self.app._open_path(self.train_dir)

    def stop_for_exit(self):
        """Called when the app closes while a training is running."""
        if self.is_running():
            self.request_stop()
            self.kill_now()
