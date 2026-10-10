"""The PKT Train window: choose a model and size, train on this PC (live log, stop, resume) or copy the code for Colab."""
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

COLAB_URL = "https://colab.research.google.com/"
POLL_MS = 150


class TrainPage:
    def __init__(self, launcher, train_dir):
        """`launcher` = the PK Transport window (gives root, texts, settings); `train_dir` = the PKT-Train folder."""
        self.launcher = launcher
        self.root = launcher.root
        self.train_dir = train_dir
        self.tr = launcher.tr
        self.proc = None
        self.reader = None
        self.log_q = queue.Queue()
        self.env_q = queue.Queue()
        self.model_var = tk.StringVar(value="")
        self.run_info = {}
        self.top = tk.Toplevel(self.root)
        self.top.geometry("980x760")
        self.top.minsize(860, 640)
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        saved = (launcher.settings.get("train") or {})
        self.family_var = tk.StringVar(value=saved.get("family") if saved.get("family") in TC.FAMILIES else "yolo26")
        self.size_var = tk.StringVar(value="")
        self.where_var = tk.StringVar(value=saved.get("where", "local"))
        self.dataset_var = tk.StringVar(value=saved.get("dataset", ""))
        self.store_var = tk.StringVar(value=saved.get("store", ""))
        self.num_vars = {k: tk.StringVar(value="") for k in TC.NUMERIC_KEYS}
        self.mode_var = tk.StringVar(value="auto")
        self.source_var = tk.StringVar(value="")
        self.copy_var = tk.StringVar(value="all")
        self.env_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar(value="")
        self.widgets = {}
        self._build()
        self.on_family_changed(initial=True)
        self.refresh_runs()
        self.check_environment()
        self.top.after(POLL_MS, self._poll)

    def t(self, key, **kw):
        return self.launcher.t(key, **kw)

    # ---------------------------------------------------------------- layout
    def _build(self):
        top = self.top
        top.title(self.t("train_title"))
        for child in top.winfo_children():
            child.destroy()
        body = ttk.Frame(top, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(3, weight=1)

        ttk.Label(body, text=self.t("train_title"), font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(body, textvariable=self.env_var, foreground="#555555").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # model + where
        ttk.Label(body, text=self.t("train_family")).grid(row=2, column=0, sticky="w")
        fam = ttk.Combobox(body, textvariable=self.family_var, values=TC.FAMILY_ORDER, state="readonly", width=14)
        fam.grid(row=2, column=1, sticky="w", padx=6)
        fam.bind("<<ComboboxSelected>>", lambda e: self.on_family_changed())
        self.widgets["family"] = fam
        ttk.Label(body, text=self.t("train_size")).grid(row=2, column=2, sticky="e")
        size = ttk.Combobox(body, textvariable=self.size_var, values=[], state="readonly", width=8)
        size.grid(row=2, column=3, sticky="w", padx=6)
        self.widgets["size"] = size
        ttk.Label(body, text=self.t("train_where")).grid(row=3, column=0, sticky="w", pady=(6, 0))
        wf = ttk.Frame(body)
        wf.grid(row=3, column=1, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Radiobutton(wf, text=self.t("train_local"), value="local", variable=self.where_var, command=self._on_where).pack(side="left")
        ttk.Radiobutton(wf, text=self.t("train_colab"), value="colab", variable=self.where_var, command=self._on_where).pack(side="left", padx=12)

        # settings (shared by local and Colab)
        sf = ttk.LabelFrame(body, text=f" {self.t('train_settings')} ", padding=8)
        sf.grid(row=4, column=0, columnspan=4, sticky="ew", pady=10)
        for i, key in enumerate(TC.NUMERIC_KEYS):
            ttk.Label(sf, text=self.t(f"train_{key}")).grid(row=0, column=i * 2, sticky="e", padx=(8 if i else 0, 2))
            ttk.Entry(sf, textvariable=self.num_vars[key], width=7).grid(row=0, column=i * 2 + 1)
        ttk.Label(sf, text=self.t("train_run_mode")).grid(row=1, column=0, sticky="e", pady=(8, 0))
        mode = ttk.Combobox(sf, textvariable=self.mode_var, values=TC.TRAINING_MODES, state="readonly", width=18)
        mode.grid(row=1, column=1, columnspan=3, sticky="w", pady=(8, 0), padx=(2, 0))
        self.widgets["mode"] = mode
        ttk.Label(sf, text=self.t("train_source_run")).grid(row=1, column=4, sticky="e", pady=(8, 0))
        ttk.Entry(sf, textvariable=self.source_var, width=12).grid(row=1, column=5, columnspan=2, sticky="w", pady=(8, 0))

        # local part
        self.local_frame = ttk.Frame(body)
        self.local_frame.grid(row=5, column=0, columnspan=4, sticky="nsew")
        self.local_frame.columnconfigure(1, weight=1)
        lf = self.local_frame
        ttk.Label(lf, text=self.t("train_dataset")).grid(row=0, column=0, sticky="w")
        ttk.Entry(lf, textvariable=self.dataset_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(lf, text=self.t("browse"), command=lambda: self._browse(self.dataset_var)).grid(row=0, column=2)
        ttk.Label(lf, text=self.t("train_store")).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(lf, textvariable=self.store_var).grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))
        ttk.Button(lf, text=self.t("browse"), command=lambda: self._browse(self.store_var)).grid(row=1, column=2, pady=(4, 0))
        bar = ttk.Frame(lf)
        bar.grid(row=2, column=0, columnspan=3, sticky="w", pady=8)
        self.start_btn = ttk.Button(bar, text=self.t("train_start"), command=self.start_training)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text=self.t("train_stop"), command=self.request_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.kill_btn = ttk.Button(bar, text=self.t("train_kill"), command=self.kill_now, state="disabled")
        self.kill_btn.pack(side="left")
        ttk.Button(bar, text=self.t("train_open_results"), command=self.open_results).pack(side="left", padx=(18, 6))
        ttk.Button(bar, text=self.t("train_open_scripts"), command=self.open_scripts).pack(side="left")
        ttk.Label(lf, textvariable=self.progress_var, font=("Segoe UI", 10, "bold"), foreground="#1f4e79").grid(row=3, column=0, columnspan=3, sticky="w")
        self._build_runs(lf)
        logf = ttk.LabelFrame(lf, text=f" {self.t('train_log')} ", padding=4)
        logf.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        lf.rowconfigure(5, weight=1)
        self.log = tk.Text(logf, height=14, wrap="none", state="disabled", font=("Consolas", 9))
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        body.rowconfigure(5, weight=1)

        # Colab part
        self.colab_frame = ttk.LabelFrame(body, text=f" {self.t('train_colab_title')} ", padding=10)
        self.colab_frame.grid(row=5, column=0, columnspan=4, sticky="nsew")
        ttk.Label(self.colab_frame, text=self.t("train_colab_help"), wraplength=860, justify="left").pack(anchor="w")
        row = ttk.Frame(self.colab_frame)
        row.pack(anchor="w", pady=10)
        ttk.Label(row, text=self.t("train_copy_what")).pack(side="left")
        self.copy_combo = ttk.Combobox(row, textvariable=self.copy_var, state="readonly", width=34)
        self.copy_combo.pack(side="left", padx=6)
        self.copy_options = []
        ttk.Button(row, text=self.t("train_copy_btn"), command=self.copy_colab_code).pack(side="left", padx=6)
        ttk.Button(row, text=self.t("train_open_colab"), command=lambda: webbrowser.open(COLAB_URL)).pack(side="left")

        ttk.Label(body, textvariable=self.status_var, foreground="#1f4e79").grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self._on_where()

    def _build_runs(self, parent):
        """The trained runs found in the Runs folder, with the buttons that hand one to PKT Analyze."""
        rf = ttk.LabelFrame(parent, text=f" {self.t('train_runs')} ", padding=6)
        rf.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        rf.columnconfigure(0, weight=1)
        cols = ("run", "model", "best_epoch", "map50", "map50_95", "usable")
        names = {"run": "col_run", "model": "col_model", "best_epoch": "col_best_epoch", "map50": "col_map50", "map50_95": "col_map50_95", "usable": "col_usable"}
        self.runs_tree = ttk.Treeview(rf, columns=cols, show="headings", height=4, selectmode="browse")
        for c in cols:
            self.runs_tree.heading(c, text=self.t(names[c]))
            self.runs_tree.column(c, width=(150 if c == "model" else 90), anchor="center" if c != "model" else "w")
        self.runs_tree.grid(row=0, column=0, sticky="ew")
        sb = ttk.Scrollbar(rf, command=self.runs_tree.yview)
        self.runs_tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        rb = ttk.Frame(rf)
        rb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(rb, text=self.t("train_refresh"), command=self.refresh_runs).pack(side="left")
        ttk.Button(rb, text=self.t("train_use_in_analyze"), command=self.use_in_analyze).pack(side="left", padx=6)
        ttk.Button(rb, text=self.t("train_open_run"), command=self.open_run).pack(side="left")
        ttk.Label(rb, textvariable=self.model_var).pack(side="left", padx=(16, 0))
        self.runs = []

    def refresh_runs(self):
        """Look for trained runs again (the folder shown in the Runs field, and its sibling families)."""
        self.runs = shared.find_runs(shared.runs_root_for(self.store_dir()))
        self.runs_tree.delete(*self.runs_tree.get_children())
        for i, r in enumerate(self.runs):
            fmt = lambda v: "" if v is None else f"{v:.3f}"
            self.runs_tree.insert("", "end", iid=str(i), values=(r["run"], r["model"] or r["family"], r["best_epoch"] if r["best_epoch"] is not None else "",
                                                                  fmt(r["map50"]), fmt(r["map50_95"]), "✓" if r["usable_in_analyze"] else "—"))
        self._show_current_model()
        return self.runs

    def _show_current_model(self):
        model = shared.get_analyze_model(self.launcher.settings)
        self.model_var.set(self.t("train_current_model", name=os.path.basename(model) if model else self.t("train_no_model")))

    def _selected_run(self):
        sel = self.runs_tree.selection()
        if not sel:
            messagebox.showinfo(self.t("app_title"), self.t("train_pick_run"), parent=self.top)
            return None
        return self.runs[int(sel[0])]

    def use_in_analyze(self):
        """Hand the best.pt of the selected run to PKT Analyze (it starts with this model from now on)."""
        run = self._selected_run()
        if run is None:
            return False
        if not run["usable_in_analyze"]:
            messagebox.showinfo(self.t("app_title"), self.t("train_not_usable"), parent=self.top)
            return False
        shared.set_analyze_model(self.launcher.settings, run["weights"])
        self.launcher._save()
        self.launcher.refresh()
        self._show_current_model()
        self.status_var.set(self.t("train_model_set", path=run["weights"]))
        return True

    def open_run(self):
        run = self._selected_run()
        if run is None:
            return False
        self.launcher._open_path(run["folder"])
        return True

    def _on_where(self):
        local = self.where_var.get() == "local"
        if local:
            self.colab_frame.grid_remove()
            self.local_frame.grid()
        else:
            self.local_frame.grid_remove()
            self.colab_frame.grid()
        self._save_choices()

    def _browse(self, var):
        path = filedialog.askdirectory(parent=self.top, initialdir=var.get() or self.train_dir)
        if path:
            var.set(os.path.normpath(path))
            self._save_choices()

    def _save_choices(self):
        self.launcher.settings["train"] = {"family": self.family_var.get(), "where": self.where_var.get(),
                                           "dataset": self.dataset_var.get(), "store": self.store_var.get()}
        self.launcher._save()

    # ---------------------------------------------------------------- model / settings
    def script(self):
        return TC.script_path(self.train_dir, self.family_var.get())

    def on_family_changed(self, initial=False):
        fam = TC.FAMILIES[self.family_var.get()]
        self.widgets["size"].configure(values=fam["sizes"])
        if not initial or self.size_var.get() not in fam["sizes"]:
            self.size_var.set(fam["default_size"])             # another family: its own default size (the language switch keeps the size)
        path = self.script()
        if os.path.isfile(path) and not (initial and self.num_vars["epochs"].get()):      # (the language switch keeps what was typed)
            d = TC.read_defaults(TC.read_text(path))
            for key in TC.NUMERIC_KEYS:
                if key in d:
                    self.num_vars[key].set(str(d[key]))
            self.mode_var.set(d.get("training_mode", "auto"))
            self.source_var.set(d.get("source_run_name", ""))
        if not self.store_var.get() or not initial:
            self.store_var.set(TC.default_store_dir(self.train_dir, self.family_var.get()))
        self._refresh_copy_options()
        self._save_choices()

    def _refresh_copy_options(self):
        labels = [self.t("train_copy_all"), self.t("train_copy_file")]
        self.copy_options = ["all", "file"]
        path = self.script()
        if os.path.isfile(path):
            for n in TC.cell_numbers(TC.read_text(path)):
                labels.append(self.t("train_copy_cell", n=n))
                self.copy_options.append(f"cell{n}")
        self.copy_combo.configure(values=labels)
        self.copy_labels = labels
        self.copy_combo.set(labels[0])

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
        return s

    # ---------------------------------------------------------------- environment
    def python_cmd(self):
        return python_command(((self.launcher.settings.get("modules") or {}).get("train") or {}).get("python", ""))

    def check_environment(self):
        self.env_var.set(self.t("train_env_checking"))
        cmd = self.python_cmd()

        def work():
            self.env_q.put(TC.probe_environment(cmd))          # shown by _poll (Tk is only touched from the main thread)

        threading.Thread(target=work, daemon=True).start()

    def _show_environment(self, info):
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
            pass                                   # the window was closed meanwhile

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
            messagebox.showerror(self.t("app_title"), self.t("train_no_script", path=self.script()), parent=self.top)
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
            messagebox.showinfo(self.t("app_title"), self.t("train_already_running"), parent=self.top)
            return None
        path = self.script()
        if not os.path.isfile(path):
            messagebox.showerror(self.t("app_title"), self.t("train_no_script", path=path), parent=self.top)
            return None
        family, size = self.family_var.get(), self.size_var.get()
        try:
            run_script, missing = TC.write_run_script(self.train_dir, family, self.current_settings(), time.strftime("%Y%m%d_%H%M%S"))
        except OSError as exc:
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.top)
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
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.top)
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
            if not self.top.winfo_exists():
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
        self.top.after(POLL_MS, self._poll)

    def _set_progress(self):
        info = self.run_info
        prog = self.t("train_progress", epoch=info["epoch"], total=info["total"] or "?") if info.get("epoch") else ""
        self.progress_var.set(self.t("train_running", family=info.get("family", ""), size=info.get("size", ""), progress=prog))

    def _on_finished(self):
        code = self.proc.returncode if self.proc else None
        self.progress_var.set("")
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
            messagebox.showerror(self.t("app_title"), str(exc), parent=self.top)
            return False
        self.status_var.set(self.t("train_stopped_flag"))
        return True

    def kill_now(self):
        if self.proc is not None:
            TC.kill_process_tree(self.proc)
        return True

    def open_results(self):
        self.launcher._open_path(self.store_dir() if os.path.isdir(self.store_dir()) else self.train_dir)

    def open_scripts(self):
        self.launcher._open_path(self.train_dir)

    def retranslate(self):
        """The window language changed: build the labels again (the values the user typed stay)."""
        self._build()
        self.on_family_changed(initial=True)
        self.refresh_runs()
        self.check_environment()

    def close(self):
        if self.is_running():
            if not messagebox.askyesno(self.t("app_title"), self.t("train_busy_close"), parent=self.top):
                return
            self.request_stop()
            self.kill_now()
        self.launcher.train_page = None
        self.top.destroy()
