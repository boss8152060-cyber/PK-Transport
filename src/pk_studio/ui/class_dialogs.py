"""Class manager and class-import dialogs for the Label tab.

The dialogs only collect decisions; every change goes through
``pk_studio.core.class_ops`` and is applied by ``tab._apply_class_ops``.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from pk_studio.core import class_ops
from pk_studio.theme import COLORS

ROW_BG = "#FFFFFF"
ROW_SELECTED_BG = "#DCE8FF"


class ClassManagerDialog(tk.Toplevel):
    """List of classes: multi-select, rename, reorder, merge, delete, add, import."""

    def __init__(self, tab):
        super().__init__(tab)
        self.tab = tab
        self.title("Manage Classes & Colors")
        self.geometry("560x640")
        self.minsize(480, 520)
        self.transient(tab)
        self.grab_set()

        self.selected = set()
        self._anchor = None
        self._counts = {}
        self._rows = {}

        ttk.Label(self, text="Classes  (click to select, Ctrl/Shift for several, double-click to rename)",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(body, highlightthickness=0, bg=ROW_BG)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=ROW_BG)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._window, width=e.width))

        self.status = ttk.Label(self, text="", foreground=COLORS["text_muted"])
        self.status.pack(anchor="w", padx=10)

        edit = ttk.Frame(self)
        edit.pack(fill="x", padx=8, pady=(4, 0))
        for text, cmd in (("✏ Rename", self.rename_selected), ("↑ Up", lambda: self.move(-1)),
                          ("↓ Down", lambda: self.move(1)), ("⛙ Merge…", self.merge_selected),
                          ("🗑 Delete", self.delete_selected)):
            ttk.Button(edit, text=text, command=cmd).pack(side="left", expand=True, fill="x", padx=2)

        add = ttk.LabelFrame(self, text="Add new class (several: separate with commas)", padding=5)
        add.pack(fill="x", padx=10, pady=6)
        self.entry = ttk.Entry(add)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda e: self.add())
        ttk.Button(add, text="Add", command=self.add).pack(side="right")

        imp = ttk.LabelFrame(self, text="Import classes", padding=5)
        imp.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Button(imp, text="From model / file…", command=self.import_from_file).pack(side="left", padx=2)
        self.btn_loaded = ttk.Button(imp, text="From loaded model", command=self.import_from_loaded_model)
        self.btn_loaded.pack(side="left", padx=2)
        ttk.Button(imp, text="Model → my classes…", command=self.map_loaded_model).pack(side="left", padx=2)

        self.bind("<Delete>", lambda e: self.delete_selected() if self.focus_get() is not self.entry else None)
        self.refresh()

    # ------------------------------------------------------------------ list
    def refresh(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._rows = {}
        self._counts = class_ops.count_class_usage(self.tab.lbl_dir)
        self.selected = {i for i in self.selected if i < len(self.tab.classes)}
        for i, name in enumerate(self.tab.classes):
            row = tk.Frame(self.inner, bg=ROW_BG)
            row.pack(fill="x", pady=1, padx=1)
            rgb = self.tab.get_class_color(i)
            swatch = tk.Button(row, width=2, relief="flat", bg=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
                               command=lambda idx=i: self.tab.choose_class_color(idx, self, self.refresh))
            swatch.pack(side="left", padx=(2, 8), pady=2)
            count = self._counts.get(i, 0)
            label = tk.Label(row, text=f"[{i + 1}] {name}", font=("Consolas", 10), bg=ROW_BG, anchor="w")
            label.pack(side="left", fill="x", expand=True)
            info = tk.Label(row, text=f"{count} boxes", font=("Segoe UI", 8), fg=COLORS["text_muted"], bg=ROW_BG)
            info.pack(side="right", padx=8)
            for w in (row, label, info):
                w.bind("<Button-1>", lambda e, idx=i: self._click(idx, e))
                w.bind("<Double-Button-1>", lambda e, idx=i: self._double(idx))
            self._rows[i] = (row, label, info)
        self._paint()

    def _paint(self):
        for i, widgets in self._rows.items():
            bg = ROW_SELECTED_BG if i in self.selected else ROW_BG
            for w in widgets:
                w.configure(bg=bg)
        n = len(self.selected)
        self.status.configure(text=f"{len(self.tab.classes)} classes" + (f"  ·  {n} selected" if n else ""))
        self.btn_loaded.state(["!disabled"] if self.tab.auto_model is not None else ["disabled"])

    def _click(self, idx, event):
        ctrl, shift = bool(event.state & 0x0004), bool(event.state & 0x0001)
        if shift and self._anchor is not None:
            lo, hi = sorted((self._anchor, idx))
            self.selected = set(range(lo, hi + 1)) | (self.selected if ctrl else set())
        elif ctrl:
            self.selected ^= {idx}
            self._anchor = idx
        else:
            self.selected = {idx}
            self._anchor = idx
        self._paint()

    def _double(self, idx):
        self.selected = {idx}
        self._paint()
        self.rename_selected()

    def _single(self, what):
        if len(self.selected) != 1:
            messagebox.showinfo("Select one class", f"Select exactly one class to {what}.", parent=self)
            return None
        return next(iter(self.selected))

    def _apply(self, build):
        try:
            change = build()
        except (ValueError, IndexError) as exc:
            messagebox.showwarning("Class change", str(exc), parent=self)
            return False
        self.tab._apply_class_ops(change)
        return True

    # --------------------------------------------------------------- actions
    def rename_selected(self):
        idx = self._single("rename")
        if idx is None:
            return
        old = self.tab.classes[idx]
        new = simpledialog.askstring("Rename class", f"New name for [{idx + 1}] {old}:", initialvalue=old, parent=self)
        if new is None or new.strip() == old:
            return
        if self._apply(lambda: class_ops.rename_class(self.tab.classes, idx, new)):
            self.refresh()

    def move(self, delta):
        idx = self._single("move")
        if idx is None or not 0 <= idx + delta < len(self.tab.classes):
            return
        if not messagebox.askyesno(
            "Change class order",
            "Changing the order changes YOLO class IDs and updates every label file in this dataset.\n\nContinue?",
            parent=self,
        ):
            return
        if self._apply(lambda: class_ops.move_class(self.tab.classes, idx, delta)):
            self.selected = {idx + delta}
            self._anchor = idx + delta
            self.refresh()

    def delete_selected(self):
        if not self.selected:
            messagebox.showinfo("Select classes", "Select one or more classes to delete.", parent=self)
            return
        idxs = sorted(self.selected)
        names = ", ".join(f"[{i + 1}] {self.tab.classes[i]}" for i in idxs)
        boxes = sum(self._counts.get(i, 0) for i in idxs)
        if not messagebox.askyesno(
            "Delete classes",
            f"Delete {len(idxs)} class(es):\n{names}\n\nThis removes {boxes} box(es) from your label files "
            "and cannot be undone.\n\nContinue?",
            parent=self,
        ):
            return
        if self._apply(lambda: class_ops.delete_classes(self.tab.classes, idxs)):
            self.selected = set()
            self.refresh()

    def merge_selected(self):
        if len(self.selected) < 2:
            messagebox.showinfo("Merge classes", "Select two or more classes to merge (Ctrl/Shift+click).", parent=self)
            return
        idxs = sorted(self.selected)
        choice = _MergeChoice(self, [(i, self.tab.classes[i]) for i in idxs])
        self.wait_window(choice)
        if choice.result is None:
            return
        target, name = choice.result
        boxes = sum(self._counts.get(i, 0) for i in idxs)
        if not messagebox.askyesno(
            "Merge classes",
            f"Merge {len(idxs)} classes into \"{name}\"?\n{boxes} box(es) in your label files will be relabeled "
            "(exact duplicate boxes created by the merge are removed).\n\nContinue?",
            parent=self,
        ):
            return
        if self._apply(lambda: class_ops.merge_classes(self.tab.classes, idxs, target, name)):
            self.selected = set()
            self.refresh()

    def add(self):
        names = [n.strip() for n in self.entry.get().split(",") if n.strip()]
        if not names:
            return
        change = class_ops.add_classes(self.tab.classes, names)
        if len(change.new_classes) == len(self.tab.classes):
            messagebox.showinfo("Add class", "Those classes already exist.", parent=self)
            return
        self.tab._apply_class_ops(change)
        self.entry.delete(0, tk.END)
        self.refresh()

    # ---------------------------------------------------------------- import
    def import_from_file(self):
        path = filedialog.askopenfilename(
            parent=self, title="Choose a model (.pt) or class list (classes.txt / data.yaml)",
            filetypes=[("Model or class list", "*.pt *.txt *.names *.yaml *.yml"), ("All files", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith(".pt"):
                if not self.tab.load_yolo_model_path(path, show_message=False, check_classes=False):
                    messagebox.showerror("Import classes", "Could not load this model.", parent=self)
                    return
                names, label, is_model = self.tab.model_class_names(), os.path.basename(path), True
            else:
                names, label, is_model = class_ops.load_class_names(path), os.path.basename(path), False
        except (OSError, ValueError, UnicodeError) as exc:
            messagebox.showerror("Import classes", str(exc), parent=self)
            return
        self._open_import(names, label, is_model)

    def import_from_loaded_model(self):
        if self.tab.auto_model is None:
            return
        self._open_import(self.tab.model_class_names(), os.path.basename(self.tab.model_path or "model"), True)

    def map_loaded_model(self):
        """Decide how each class of the loaded model maps to your classes (Auto-Label)."""
        if self.tab.auto_model is None:
            path = filedialog.askopenfilename(parent=self, title="Select YOLO model (best.pt)",
                                              filetypes=[("PyTorch Model", "*.pt")])
            if not path or not self.tab.load_yolo_model_path(path, show_message=False, check_classes=False):
                return
        self._open_import(self.tab.model_class_names(), os.path.basename(self.tab.model_path or "model"),
                          True, default_mode="match")

    def _open_import(self, names, label, is_model, default_mode="replace"):
        dlg = ClassImportDialog(self, self.tab, names, label, is_model, default_mode)
        self.wait_window(dlg)
        self.refresh()


class _MergeChoice(tk.Toplevel):
    """Pick which class to keep and the merged name."""

    def __init__(self, parent, items):
        super().__init__(parent)
        self.title("Merge classes")
        self.transient(parent)
        self.grab_set()
        self.result = None
        ttk.Label(self, text="Keep which class id?", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        self.target = tk.IntVar(value=items[0][0])
        self.name = tk.StringVar(value=items[0][1])
        self._names = dict(items)
        for idx, name in items:
            ttk.Radiobutton(self, text=f"[{idx + 1}] {name}", variable=self.target, value=idx,
                            command=lambda: self.name.set(self._names[self.target.get()])).pack(anchor="w", padx=24)
        ttk.Label(self, text="Merged class name:").pack(anchor="w", padx=12, pady=(10, 0))
        ttk.Entry(self, textvariable=self.name, width=32).pack(padx=12, pady=(0, 8))
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(bar, text="Merge", command=self._ok).pack(side="right", padx=4)

    def _ok(self):
        if not self.name.get().strip():
            messagebox.showwarning("Merge classes", "Enter a name.", parent=self)
            return
        self.result = (self.target.get(), self.name.get().strip())
        self.destroy()


class ClassImportDialog(tk.Toplevel):
    """Adopt a class list (model or file) or map it onto your existing classes."""

    NEW, SKIP = "＋ New class", "✕ Skip (ignore)"

    def __init__(self, parent, tab, source_names, source_label, is_model, default_mode="replace"):
        super().__init__(parent)
        self.tab = tab
        self.source = list(source_names)
        self.is_model = is_model
        self.title(f"Classes from {source_label}")
        self.geometry("620x620")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=f"{source_label} has {len(self.source)} classes. How should they be used?",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        self.mode = tk.StringVar(value=default_mode if tab.classes else "replace")
        ttk.Radiobutton(
            self, variable=self.mode, value="replace", command=self._sync,
            text="Use these as my class list (replace). Labels I already made follow by name;\n"
                 "my classes that match none of them are kept at the end.",
        ).pack(anchor="w", padx=16, pady=2)
        ttk.Radiobutton(
            self, variable=self.mode, value="match", command=self._sync,
            text="Keep my classes and choose where each one goes (map / merge / skip / add new).",
        ).pack(anchor="w", padx=16, pady=2)

        self.table = ttk.LabelFrame(self, text="Map each class", padding=6)
        self.table.pack(fill="both", expand=True, padx=12, pady=6)
        canvas = tk.Canvas(self.table, highlightthickness=0)
        scroll = ttk.Scrollbar(self.table, orient="vertical", command=canvas.yview)
        self.rows = tk.Frame(canvas)
        canvas.create_window((0, 0), window=self.rows, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.rows.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.options = [f"→ [{i + 1}] {c}" for i, c in enumerate(tab.classes)] + [self.NEW, self.SKIP]
        self.combos = {}
        saved = getattr(tab, "model_class_map", {}) if is_model else {}
        matches = class_ops.auto_match(self.source, tab.classes)
        for r, name in enumerate(self.source):
            ttk.Label(self.rows, text=name, width=24, anchor="w").grid(row=r, column=0, sticky="w", padx=2, pady=2)
            ttk.Label(self.rows, text="⟶").grid(row=r, column=1, padx=4)
            combo = ttk.Combobox(self.rows, values=self.options, state="readonly", width=32)
            combo.grid(row=r, column=2, sticky="w", pady=2)
            combo.set(self._initial_choice(name, saved, matches))
            combo.bind("<<ComboboxSelected>>", lambda e: self._summary())
            self.combos[name] = combo

        self.summary = ttk.Label(self, text="", foreground=COLORS["text_muted"])
        self.summary.pack(anchor="w", padx=14)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=10)
        ttk.Button(bar, text="Auto-match", command=self._auto).pack(side="left", padx=2)
        ttk.Button(bar, text="All → new class", command=lambda: self._set_all(self.NEW)).pack(side="left", padx=2)
        ttk.Button(bar, text="All → skip", command=lambda: self._set_all(self.SKIP)).pack(side="left", padx=2)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="right", padx=4)
        self._sync()

    def _initial_choice(self, name, saved, matches):
        if name in saved:
            target = saved[name]
            if target in self.tab.classes:
                return self.options[self.tab.classes.index(target)]
            return self.SKIP
        target = matches.get(name)
        if target is not None:
            return self.options[self.tab.classes.index(target)]
        return self.NEW

    def _auto(self):
        matches = class_ops.auto_match(self.source, self.tab.classes)
        for name, combo in self.combos.items():
            combo.set(self._initial_choice(name, {}, matches))
        self._summary()

    def _set_all(self, value):
        for combo in self.combos.values():
            combo.set(value)
        self._summary()

    def _sync(self):
        state = "readonly" if self.mode.get() == "match" else "disabled"
        for combo in self.combos.values():
            combo.configure(state=state)
        self._summary()

    def _summary(self):
        if self.mode.get() == "replace":
            self.summary.configure(text=f"Your class list becomes these {len(self.source)} classes.")
            return
        values = [c.get() for c in self.combos.values()]
        new = values.count(self.NEW)
        skip = values.count(self.SKIP)
        self.summary.configure(text=f"{len(values) - new - skip} mapped to existing · {new} added as new · {skip} skipped")

    def apply(self):
        tab = self.tab
        if self.mode.get() == "replace":
            if tab.classes and not messagebox.askyesno(
                "Replace class list",
                "Your class list will be replaced and label files updated to the new class IDs.\n\nContinue?",
                parent=self,
            ):
                return
            tab._apply_class_ops(class_ops.replace_with(tab.classes, self.source))
            if self.is_model:
                tab.set_model_class_map({})
            self.destroy()
            return

        choices = {name: combo.get() for name, combo in self.combos.items()}
        new_names = [n for n, c in choices.items() if c == self.NEW]
        if new_names:
            tab._apply_class_ops(class_ops.add_classes(tab.classes, new_names))
        mapping = {}
        for name, choice in choices.items():
            if choice == self.NEW:
                mapping[name] = name
            elif choice == self.SKIP:
                mapping[name] = None
            else:
                mapping[name] = tab.classes[self.options.index(choice)]
        if self.is_model:
            tab.set_model_class_map(mapping)
        self.destroy()
