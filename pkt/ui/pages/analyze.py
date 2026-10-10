"""PKT Analyze inside this window: its main window class (Run1App in PKT-Analyze/Run/PKStudio.py) is built into a frame of this page.

The code stays in the PKT-Analyze repo. PKStudio.py is imported in a background thread the first time the page is shown (it loads
PyTorch / Ultralytics, which takes a few seconds); Run1App then gets a frame that behaves like its root window."""
import importlib
import os
import queue
import sys
import threading
import tkinter as tk
import traceback
from tkinter import ttk

from pkt import shared
from pkt.ui.theme import COLORS

BOOTSTRAP_MARKER = "PK_STUDIO_CUDA_RELAUNCHED"      # PKStudio.py would restart itself with another Python at import time; this window already chose its Python


class EmbeddedRoot(tk.Frame):
    """A frame that can stand in for the Tk root of Run1App: the window-level calls do nothing here (the window belongs to PK Transport)."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg"])
        self.close_handler = None

    def title(self, *_a, **_k):
        return ""

    def geometry(self, *_a, **_k):
        return ""

    def minsize(self, *_a, **_k):
        return None

    def state(self, *_a, **_k):
        return ""

    def iconbitmap(self, *_a, **_k):
        return None

    def attributes(self, *_a, **_k):
        return None

    def protocol(self, name=None, func=None):
        if name == "WM_DELETE_WINDOW":
            self.close_handler = func

    def bind_all(self, sequence=None, func=None, add=None):
        """Run1App binds the mouse wheel for all windows; here it must add to what is bound and only act while this page is showing."""
        if func is None:
            return super().bind_all(sequence)

        def gated(event, _f=func):
            if self.winfo_ismapped():
                return _f(event)
            return None
        return super().bind_all(sequence, gated, add="+")


class AnalyzePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.b = app.b
        self.loaded = False
        self.loading = False
        self.error = None
        self.studio = None                  # the Run1App
        self.shell = None                   # the EmbeddedRoot
        self.applied_model = None
        self.q = queue.Queue()
        self.message = ttk.Label(self, text="", style="Muted.TLabel", justify="left", wraplength=800)
        self.message.pack(anchor="nw", padx=30, pady=30)
        app.b.on_change(self._on_language)

    def _on_language(self):
        if self.loading:
            self.message.configure(text=self.app.t("analyze_loading"))
        elif self.error:
            self.message.configure(text=self.app.t("analyze_load_failed", err=self.error))

    # ---------------------------------------------------------------- loading
    def on_show(self):
        if not self.loaded and not self.loading:
            self.load()
        elif self.studio is not None:
            self._apply_model()

    def load(self):
        _d, info = self.app.info_of("analyze")
        script = info["entry_path"]
        if not info["exists"] or not script or not os.path.isfile(script):
            self.loaded = True
            self.error = self.app.t("module_missing", name="PKT Analyze", path=info["folder"])
            self.message.configure(text=self.error)
            return
        self.loading = True
        self.message.configure(text=self.app.t("analyze_loading"))
        folder = info["folder"]
        chosen_model = shared.get_analyze_model(self.app.settings)

        def work():
            had_marker = BOOTSTRAP_MARKER in os.environ
            old_model = os.environ.get("PKT_MODEL_PATH")
            try:
                if folder not in sys.path:
                    sys.path.insert(0, folder)
                os.environ[BOOTSTRAP_MARKER] = "1"
                if chosen_model:
                    os.environ["PKT_MODEL_PATH"] = chosen_model
                module = importlib.import_module(os.path.splitext(os.path.basename(script))[0])
                self.q.put(("ok", module))
            except BaseException:                           # SystemExit included: PKStudio.py must never end this program
                self.q.put(("error", traceback.format_exc(limit=3)))
            finally:
                if not had_marker:
                    os.environ.pop(BOOTSTRAP_MARKER, None)
                if old_model is None:
                    os.environ.pop("PKT_MODEL_PATH", None)
                else:
                    os.environ["PKT_MODEL_PATH"] = old_model

        threading.Thread(target=work, daemon=True).start()
        self.after(150, self._poll)

    def _poll(self):
        try:
            kind, payload = self.q.get_nowait()
        except queue.Empty:
            if self.winfo_exists():
                self.after(150, self._poll)
            return
        self.loading = False
        self.loaded = True
        if kind == "error":
            self.error = payload
            self.message.configure(text=self.app.t("analyze_load_failed", err=payload))
            return
        self.message.pack_forget()
        self.shell = EmbeddedRoot(self)
        self.shell.pack(fill="both", expand=True)
        try:
            self.studio = payload.Run1App(self.shell)
        except Exception:
            self.shell.destroy()
            self.shell = None
            self.error = traceback.format_exc(limit=3)
            self.message.pack(anchor="nw", padx=30, pady=30)
            self.message.configure(text=self.app.t("analyze_load_failed", err=self.error))
            return
        self.applied_model = self.studio.model_var.get()
        self._apply_model()

    # ---------------------------------------------------------------- shared model / closing
    def _apply_model(self):
        """A model sent here from PKT Train (or set in the settings) is put into the Model field once."""
        chosen = shared.get_analyze_model(self.app.settings)
        if chosen and chosen != self.applied_model and os.path.isfile(chosen):
            self.studio.model_var.set(chosen)
            self.applied_model = chosen

    def is_running(self):
        return bool(self.studio is not None and getattr(self.studio, "running", False))

    def stop_for_exit(self):
        """The window is closing while an analysis runs: ask it to stop (it finishes the current frame)."""
        if self.studio is not None:
            self.studio.stop_event.set()
            self.studio.pause_event.set()
