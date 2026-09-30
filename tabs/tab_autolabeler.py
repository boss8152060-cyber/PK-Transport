"""
=========================================================================
PK Studio - Tab: Auto-Labeler (Annotation + Auto-Label รวมกัน)

แปลงมาจาก annotation_tool_py.py (AnnotationStudio) — logic การวาดกรอบ,
undo/redo, class manager, filter, keyboard shortcuts ทั้งหมดเหมือนเดิม
ทุกประการ เพิ่มเข้ามาใหม่คือระบบ Auto-Label ด้วย YOLO (ปุ่ม Load Model,
Auto-Label Current, Batch Auto-Label) ให้ตีกรอบอัตโนมัติแล้วมาแก้ไขต่อใน
เครื่องมือเดียวกันได้เลย ไม่ต้องสลับไปมาระหว่างเครื่องมือ

Features เดิมจาก annotation_tool_py.py:
  1. Updated App Title: เปลี่ยนชื่อโปรแกรมเป็น "PK Studio"
  2. Color Format Correction: แปลงค่าสี RGB -> BGR ก่อนส่งให้ OpenCV วาดภาพ
     ทำให้สีกล่องบน Canvas ตรงกับจานสีใน Manage Classes 100%
  3. Jump to Specific Image: พิมพ์เลขลำดับรูปภาพ + Enter เพื่อกระโดดไปรูปนั้นทันที
  4. BBox Status Filter: กรองภาพตาม Labeled / Unlabeled
  5. Auto-Review Navigation: กด Next ► เพื่อ Review + ขยับไปรูปถัดไป

Batch Auto-Label: ข้ามรูปที่มี label อยู่แล้วเสมอ (ไม่ทับ label ที่ตรวจแก้ไปแล้ว)
=========================================================================
"""

import json
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
import cv2
import numpy as np
from PIL import Image, ImageTk

from theme import COLORS

DEFAULT_COLORS = [
    (255, 56, 56),   (255, 157, 151), (255, 112, 31), (255, 178, 29),
    (207, 210, 49),  (72, 249, 10),   (14, 249, 148),  (200, 54, 249),
    (56, 180, 255),  (130, 100, 255)
]

CONFIG_FILE = ".pk_ui_config.json"

class AutoLabelerTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=0)

        # Data State
        self.src_dir = ""
        self.img_dir = ""
        self.lbl_dir = ""
        self.meta_file = ""
        self.cls_file = ""

        # Auto-Label (YOLO) State
        self.model_path = ""
        self.auto_model = None
        self.conf_threshold = 0.35
        self.imgsz = 640
        self._batch_running = False

        self.classes = []
        self.class_colors = {}     # {cls_id: (r, g, b)}
        self.image_files = []
        self.filtered_images = []
        self.current_idx = 0
        self.meta_data = {}

        # Bbox State
        self.cv_img = None
        self.orig_w, self.orig_h = 1, 1
        self.bboxes = []
        self.history = []
        self.history_idx = -1
        
        # Interactive Canvas States
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.selected_box_idx = None
        self.drag_mode = None
        self.drag_start = (0, 0)
        self.initial_bbox = None

        # Filter & Visibility State
        self.visible_classes = {}
        self.search_classes = {}
        self.search_mode = "OR"

        # Mouse Gesture Trackers
        self.pending_right_click = False
        self.last_right_click_time = 0
        self.last_left_click_time = 0

        # Typing Buffer for Class Change
        self.class_input_buffer = ""

        # Load Saved UI Config
        self.ui_config = self._load_ui_config()

        self._build_ui()
        self._bind_shortcuts()

    # =========================================================================
    # UI Setup
    # =========================================================================
    def _build_ui(self):
        # Top Control Bar
        top_bar = ttk.Frame(self, padding=(8, 6))
        top_bar.pack(fill="x", side="top")

        ttk.Button(top_bar, text="📁 Open", command=self.load_dataset).pack(side="left", padx=2)
        ttk.Button(top_bar, text="💾 Save", command=self.save_current).pack(side="left", padx=2)
        ttk.Button(top_bar, text="💾 Save All", command=self.save_all).pack(side="left", padx=2)

        ttk.Separator(top_bar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(top_bar, text="↶ Undo", command=self.undo).pack(side="left", padx=2)
        ttk.Button(top_bar, text="↷ Redo", command=self.redo).pack(side="left", padx=2)

        ttk.Separator(top_bar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(top_bar, text="🤖 Model", command=self.load_yolo_model).pack(side="left", padx=2)
        ttk.Button(top_bar, text="⚡ Auto-Label", command=self.auto_label_current_image).pack(side="left", padx=2)
        ttk.Button(top_bar, text="🚀 Batch", command=self.run_batch_autolabel).pack(side="left", padx=2)

        ttk.Separator(top_bar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(top_bar, text="🏷️ Classes", command=self.open_class_manager_window).pack(side="left", padx=2)
        ttk.Button(top_bar, text="🔍 Search", command=self.open_search_filter_window).pack(side="left", padx=2)
        ttk.Button(top_bar, text="⌨️ Shortcuts", command=self.open_shortcut_cheatsheet_window).pack(side="left", padx=2)

        self.lbl_progress = ttk.Label(top_bar, text="Reviewed: 0/0 | Total: 0", font=("Segoe UI", 9, "bold"))
        self.lbl_progress.pack(side="right", padx=15)

        # Main Paned Window
        self.main_paned = ttk.PanedWindow(self, orient="horizontal")
        self.main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(self.main_paned)
        right_frame = ttk.Frame(self.main_paned)

        self.main_paned.add(left_frame, weight=3)
        self.main_paned.add(right_frame, weight=1)

        # Canvas Toolbar
        filter_bar = ttk.Frame(left_frame, padding=2)
        filter_bar.pack(fill="x", side="top")

        ttk.Label(filter_bar, text="Status Filter:").pack(side="left", padx=2)
        self.filter_var = tk.StringVar(value="All")
        
        cb_filter = ttk.Combobox(
            filter_bar, textvariable=self.filter_var, 
            values=["All", "Reviewed", "Unreviewed", "Labeled", "Unlabeled"], 
            state="readonly", width=12
        )
        cb_filter.pack(side="left", padx=2)
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self.apply_image_filters())

        ttk.Label(filter_bar, text="Zoom:").pack(side="right", padx=2)
        self.lbl_zoom = ttk.Label(filter_bar, text="100%", width=6)
        self.lbl_zoom.pack(side="right", padx=2)
        ttk.Button(filter_bar, text="-", width=2, command=lambda: self.change_zoom(-0.15)).pack(side="right")
        ttk.Button(filter_bar, text="+", width=2, command=lambda: self.change_zoom(0.15)).pack(side="right")
        ttk.Button(filter_bar, text="Reset", command=self.reset_zoom).pack(side="right", padx=2)

        # Canvas
        self.canvas = tk.Canvas(left_frame, bg=COLORS["sidebar_bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_right_click_start)
        self.canvas.bind("<B3-Motion>", self.on_right_click_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # Bottom Bar
        bot_bar = ttk.Frame(left_frame, padding=5)
        bot_bar.pack(fill="x", side="bottom")

        ttk.Button(bot_bar, text="◄ Prev", command=self.prev_image).pack(side="left", padx=4)
        ttk.Button(bot_bar, text="Next ►", command=self.next_image).pack(side="left", padx=4)

        ttk.Separator(bot_bar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(bot_bar, text="Jump to Image:").pack(side="left", padx=(2, 2))
        self.entry_jump = ttk.Entry(bot_bar, width=6)
        self.entry_jump.pack(side="left", padx=2)
        self.entry_jump.bind("<Return>", lambda e: self.jump_to_image())
        
        ttk.Button(bot_bar, text="Go", width=4, command=self.jump_to_image).pack(side="left", padx=2)

        self.lbl_file_info = ttk.Label(bot_bar, text="No dataset loaded")
        self.lbl_file_info.pack(side="right", padx=5)

        # Right Panel Structure
        self.right_paned = ttk.PanedWindow(right_frame, orient="vertical")
        self.right_paned.pack(fill="both", expand=True)

        top_right_box = ttk.Frame(self.right_paned)
        bot_right_box = ttk.Frame(self.right_paned)

        self.right_paned.add(top_right_box, weight=1)
        self.right_paned.add(bot_right_box, weight=4)

        # Active Class Setup Frame
        cls_frame = ttk.LabelFrame(top_right_box, text="Active Class Setup", padding=5)
        cls_frame.pack(fill="both", expand=True)
        
        ttk.Label(cls_frame, text="Active Class for new box:").pack(anchor="w")
        self.cb_classes = ttk.Combobox(cls_frame, state="readonly")
        self.cb_classes.pack(fill="x", pady=(2, 2))
        self.cb_classes.bind("<<ComboboxSelected>>", lambda e: self.apply_class_change())

        self.lbl_typing_feedback = ttk.Label(cls_frame, text="Type Class ID + Enter to apply", font=("Segoe UI", 8, "italic"), foreground=COLORS["accent"])
        self.lbl_typing_feedback.pack(anchor="w")

        # UNIFIED PANEL: Current Image Boxes
        unified_frame = ttk.LabelFrame(bot_right_box, text="📦 Current Image Boxes & Visibility", padding=5)
        unified_frame.pack(fill="both", expand=True)

        self.unified_container = ttk.Frame(unified_frame)
        self.unified_container.pack(fill="both", expand=True)

        # All Dataset Summary Section
        summary_group = ttk.LabelFrame(bot_right_box, text="📊 All Dataset Summary", padding=5)
        summary_group.pack(fill="both", expand=True, pady=(5, 0))

        self.global_stats_text = tk.Text(
            summary_group, font=("Consolas", 9),
            bg=COLORS["card_bg"], fg=COLORS["text_dark"], insertbackground=COLORS["text_dark"],
            state="disabled", height=8, relief="flat", highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.global_stats_text.pack(fill="both", expand=True, side="left")
        global_scroll = ttk.Scrollbar(summary_group, orient="vertical", command=self.global_stats_text.yview)
        global_scroll.pack(side="right", fill="y")
        self.global_stats_text.config(yscrollcommand=global_scroll.set)

        self.after(100, self._restore_ui_config)

    # =========================================================================
    # Persistence & Configs
    # =========================================================================
    def _load_ui_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_ui_config(self):
        try:
            config = {
                "main_sash": self.main_paned.sashpos(0),
                "right_sash_0": self.right_paned.sashpos(0),
                "class_colors": {str(k): list(v) for k, v in self.class_colors.items()}
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def _restore_ui_config(self):
        try:
            if "main_sash" in self.ui_config:
                self.main_paned.sashpos(0, self.ui_config["main_sash"])
            if "right_sash_0" in self.ui_config:
                self.right_paned.sashpos(0, self.ui_config["right_sash_0"])
            if "class_colors" in self.ui_config:
                self.class_colors = {int(k): tuple(v) for k, v in self.ui_config["class_colors"].items()}
        except Exception:
            pass

    def _on_close(self):
        self._save_ui_config()
        self.destroy()

    # =========================================================================
    # Jump to Specific Image Engine
    # =========================================================================
    def jump_to_image(self):
        if not self.filtered_images:
            return
        
        val = self.entry_jump.get().strip()
        if not val.isdigit():
            messagebox.showwarning("Warning", "กรุณากรอกตัวเลขอ้างอิงลำดับรูปภาพ!")
            return

        target_num = int(val)
        if 1 <= target_num <= len(self.filtered_images):
            self.current_idx = target_num - 1
            self.load_current_image()
            self.entry_jump.delete(0, tk.END)
            self.focus_set()
        else:
            messagebox.showerror("Error", f"ลำดับรูปไม่อยู่ในช่วง! (มีภาพช่วง 1 ถึง {len(self.filtered_images)})")

    # =========================================================================
    # Cheat Sheet Window
    # =========================================================================
    def open_shortcut_cheatsheet_window(self):
        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts Cheat Sheet")
        win.geometry("550x500")
        win.grab_set()

        ttk.Label(win, text="⌨️ ตารางคีย์ลัดและคำสั่งทั้งหมด", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=15, pady=10)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        columns = ("key", "action")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        tree.heading("key", text="คีย์ลัด / การกระทำ")
        tree.heading("action", text="หน้าที่การทำงาน")
        
        tree.column("key", width=180, anchor="w")
        tree.column("action", width=320, anchor="w")

        shortcuts_data = [
            ("A / ฟ", "ย้อนกลับไปรูปภาพก่อนหน้า"),
            ("D / ก / Space", "ยืนยันตรวจ (Review) + ไปรูปถัดไป"),
            ("ตัวเลข (0-9)", "พิมพ์รหัส Class ID (กด Enter ยืนยัน)"),
            ("Backspace", "ลบตัวเลขที่พิมพ์ / ลบ Bbox ที่เลือก"),
            ("Delete", "ลบ Bbox ที่เลือกอยู่"),
            ("คลิกขวา ➔ คลิกซ้าย", "คลิกขวาที่ Bbox แล้วคลิกซ้ายซ้ำเพื่อลบ"),
            ("Ctrl + S / ห", "บันทึกข้อมูลรูปภาพปัจจุบัน"),
            ("Ctrl + Z / ผ", "เลิกทำ (Undo)"),
            ("Ctrl + Y / บ", "ทำซ้ำ (Redo)"),
            ("Escape", "ยกเลิกการพิมพ์ Class ID"),
            ("Scroll Wheel", "ซูมเข้า / ซูมออก (Zoom In/Out)"),
            ("คลิกขวา + ลาก", "เลื่อนมุมมองรูปภาพ (Pan)"),
            ("ดับเบิลคลิกซ้าย (พื้นว่าง)", "ย้อนกลับไปรูปก่อนหน้า"),
            ("ดับเบิลคลิกขวา (พื้นว่าง)", "ยืนยัน Review + ไปรูปถัดไป")
        ]

        for item in shortcuts_data:
            tree.insert("", tk.END, values=item)

        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    # =========================================================================
    # Class Manager & Color Palette Window
    # =========================================================================
    def open_class_manager_window(self):
        win = tk.Toplevel(self)
        win.title("Manage Classes & Colors")
        win.geometry("420x520")
        win.grab_set()

        ttk.Label(win, text="🏷️ Dataset Class & Color Palette", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=5)

        list_frame = ttk.Frame(win, padding=5)
        list_frame.pack(fill="both", expand=True, padx=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        selected_cls_idx = [None]

        def refresh_manager_list():
            for w in inner.winfo_children():
                w.destroy()

            for i, c in enumerate(self.classes):
                row = ttk.Frame(inner)
                row.pack(fill="x", anchor="w", pady=2, padx=2)

                rgb = self.get_class_color(i)
                hex_col = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

                btn_color = tk.Button(
                    row, width=2, height=1, bg=hex_col, relief="flat",
                    command=lambda idx=i: self.choose_class_color(idx, win, refresh_manager_list)
                )
                btn_color.pack(side="left", padx=(0, 6))

                lbl = ttk.Label(row, text=f"[{i + 1}] {c}", font=("Consolas", 10))
                lbl.pack(side="left")

                def select_row(idx=i):
                    selected_cls_idx[0] = idx

                row.bind("<Button-1>", lambda e, idx=i: select_row(idx))
                lbl.bind("<Button-1>", lambda e, idx=i: select_row(idx))

            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        refresh_manager_list()

        add_frame = ttk.LabelFrame(win, text="Add New Class", padding=5)
        add_frame.pack(fill="x", padx=10, pady=5)

        entry_name = ttk.Entry(add_frame)
        entry_name.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def add_cls():
            name = entry_name.get().strip()
            if name and name not in self.classes:
                old_classes = list(self.classes)
                self.classes.append(name)
                self.classes = sorted(self.classes, key=lambda x: x.lower())
                self._update_classes_after_change(old_classes)
                refresh_manager_list()
                entry_name.delete(0, tk.END)

        ttk.Button(add_frame, text="Add", command=add_cls).pack(side="right")

        def del_cls():
            if selected_cls_idx[0] is not None:
                del_idx = selected_cls_idx[0]
                del_name = self.classes[del_idx]
                if messagebox.askyesno("Confirm", f"Delete class [{del_idx + 1}] {del_name}?"):
                    old_classes = list(self.classes)
                    self.classes.remove(del_name)
                    self.bboxes = [b for b in self.bboxes if b[0] != del_idx]
                    self._update_classes_after_change(old_classes)
                    selected_cls_idx[0] = None
                    refresh_manager_list()

        ttk.Button(win, text="🗑️ Delete Selected Class", command=del_cls).pack(fill="x", padx=10, pady=5)

    def choose_class_color(self, cls_idx, parent_win=None, callback=None):
        curr_rgb = self.get_class_color(cls_idx)
        curr_hex = f"#{curr_rgb[0]:02x}{curr_rgb[1]:02x}{curr_rgb[2]:02x}"
        
        color_code = colorchooser.askcolor(
            title=f"Choose Color for [{cls_idx + 1}] {self.classes[cls_idx]}", 
            initialcolor=curr_hex,
            parent=parent_win or self
        )
        if color_code and color_code[0]:
            rgb = tuple(map(int, color_code[0]))
            self.class_colors[cls_idx] = rgb
            self._save_ui_config()
            self.update_box_list()
            self.render()
            if callback:
                callback()

    def get_class_color(self, cls_idx):
        if cls_idx in self.class_colors:
            return self.class_colors[cls_idx]
        return DEFAULT_COLORS[cls_idx % len(DEFAULT_COLORS)]

    def open_search_filter_window(self):
        if not self.classes:
            messagebox.showinfo("Info", "No classes available to filter.")
            return

        win = tk.Toplevel(self)
        win.title("Advanced Image Search Filter")
        win.geometry("450x550")

        ttk.Label(win, text="🔍 Filter Images by Class Occurrence", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=5)

        mode_frame = ttk.LabelFrame(win, text="Matching Rule", padding=5)
        mode_frame.pack(fill="x", padx=10, pady=5)

        mode_var = tk.StringVar(value=self.search_mode)
        ttk.Radiobutton(mode_frame, text="OR (Has AT LEAST ONE selected class)", variable=mode_var, value="OR").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="AND (Must contain ALL selected classes together)", variable=mode_var, value="AND").pack(anchor="w")

        cls_frame = ttk.LabelFrame(win, text="Select Classes to Search", padding=5)
        cls_frame.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = tk.Canvas(cls_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(cls_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        chk_vars = {}
        for i, c in enumerate(self.classes):
            var = tk.BooleanVar(value=self.search_classes.get(i, False))
            chk_vars[i] = var
            ttk.Checkbutton(inner, text=f"[{i + 1}] {c}", variable=var).pack(anchor="w", pady=2)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def apply_search():
            self.search_mode = mode_var.get()
            self.search_classes = {i: v.get() for i, v in chk_vars.items()}
            self.apply_image_filters()
            win.destroy()

        def reset_search():
            self.search_classes = {}
            self.apply_image_filters()
            win.destroy()

        btn_frame = ttk.Frame(win, padding=5)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Apply Filter", command=apply_search).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Reset Search", command=reset_search).pack(side="right", padx=4)

    # =========================================================================
    # Unified Checklist Panel
    # =========================================================================
    def _update_classes_after_change(self, old_classes):
        if self.cls_file:
            with open(self.cls_file, "w", encoding="utf-8") as f:
                f.write("\n".join(self.classes))

        old_to_new = {old_idx: self.classes.index(name) for old_idx, name in enumerate(old_classes) if name in self.classes}
        
        new_bboxes = []
        for bbox in self.bboxes:
            if bbox[0] in old_to_new:
                bbox[0] = old_to_new[bbox[0]]
                new_bboxes.append(bbox)
        self.bboxes = new_bboxes

        display_classes = [f"[{i + 1}] {c}" for i, c in enumerate(self.classes)]
        self.cb_classes["values"] = display_classes
        if self.classes:
            self.cb_classes.current(0)

        self.update_box_list()
        self.render()

    def update_box_list(self):
        for widget in self.unified_container.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.unified_container, highlightthickness=0)
        scroll = ttk.Scrollbar(self.unified_container, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        local_cls_counts = {}
        for cls_id, _, _, _, _ in self.bboxes:
            local_cls_counts[cls_id] = local_cls_counts.get(cls_id, 0) + 1

        for i, c in enumerate(self.classes):
            if i not in self.visible_classes:
                self.visible_classes[i] = True

            count = local_cls_counts.get(i, 0)
            var = tk.BooleanVar(value=self.visible_classes[i])

            def make_cmd(cls_idx=i, v=var):
                return lambda: self._toggle_visibility(cls_idx, v.get())

            row = ttk.Frame(inner)
            row.pack(fill="x", anchor="w", pady=2, padx=2)

            chk = ttk.Checkbutton(row, variable=var, command=make_cmd())
            chk.pack(side="left")

            rgb = self.get_class_color(i)
            hex_col = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            
            color_swatch = tk.Frame(row, width=12, height=12, bg=hex_col)
            color_swatch.pack(side="left", padx=(0, 6))

            lbl_text = f"[{i + 1}] {c} ({count})"
            lbl = ttk.Label(row, text=lbl_text, font=("Consolas", 9, "bold" if count > 0 else "normal"))
            lbl.pack(side="left")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.update_stats()

    def _toggle_visibility(self, cls_idx, is_visible):
        self.visible_classes[cls_idx] = is_visible
        self.render()

    # =========================================================================
    # Image Filters
    # =========================================================================
    def apply_image_filters(self):
        if not self.image_files:
            return

        status_filter = self.filter_var.get()
        active_search_classes = [i for i, v in self.search_classes.items() if v]

        self.filtered_images = []
        for img_name in self.image_files:
            is_rev = self.meta_data.get(img_name, {}).get("reviewed", False)
            if status_filter == "Reviewed" and not is_rev:
                continue
            if status_filter == "Unreviewed" and is_rev:
                continue

            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = os.path.join(self.lbl_dir, txt_name)
            has_bbox = False
            img_classes = set()

            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            has_bbox = True
                            img_classes.add(int(parts[0]))

            if status_filter == "Labeled" and not has_bbox:
                continue
            if status_filter == "Unlabeled" and has_bbox:
                continue

            if active_search_classes:
                if self.search_mode == "OR":
                    if not any(c in img_classes for c in active_search_classes):
                        continue
                elif self.search_mode == "AND":
                    if not all(c in img_classes for c in active_search_classes):
                        continue

            self.filtered_images.append(img_name)

        self.current_idx = 0
        self.load_current_image()

    # =========================================================================
    # Shortcuts Engine
    # =========================================================================
    def _bind_shortcuts(self):
        # ผูกกับ winfo_toplevel() (หน้าต่างหลักทั้งแอพ) ไม่ใช่ self (แท็บ Frame เอง)
        # เพราะ Frame ไม่เคยได้รับ keyboard focus จริงในการใช้งานปกติ ถ้าผูกกับ self
        # ตรง ๆ คีย์ลัดจะไม่ทำงานเลยไม่ว่าจะกดปุ่มไหนก็ตาม (เจอบั๊กนี้จริงตอนใช้งาน)
        self.winfo_toplevel().bind("<KeyPress>", self._on_global_keypress)

    def _on_global_keypress(self, event):
        if isinstance(self.focus_get(), (ttk.Entry, tk.Entry, tk.Text)):
            return

        code = event.keycode
        state = event.state
        char = event.char
        ctrl_pressed = (state & 0x0004) != 0 or (state & 0x0001) != 0

        if ctrl_pressed and (code == 83 or char in ['s', 'S', 'ห']):
            self.save_current()
            return "break"
        if ctrl_pressed and (code == 90 or char in ['z', 'Z', 'ผ']):
            self.undo()
            return "break"
        if ctrl_pressed and (code == 89 or char in ['y', 'Y', 'บ']):
            self.redo()
            return "break"

        if not ctrl_pressed:
            if code == 65 or char in ['a', 'A', 'ฟ']:
                self.prev_image()
                return "break"
            if code == 68 or char in ['d', 'D', 'ก'] or code == 32 or char == ' ':
                self.next_image()
                return "break"

            if code == 13 or event.keysym in ['Return', 'KP_Enter']:
                self.on_key_enter()
                return "break"
            if code == 27 or event.keysym == 'Escape':
                self.clear_typing_buffer()
                return "break"

            if event.keysym in ['Delete', 'BackSpace'] or code in [46, 8]:
                self.on_key_backspace()
                return "break"

            digit_map = {
                '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
                '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
                '_': '0', 'จ': '0',
                '!:': '1', 'ๅ': '1',
                '@': '2', '/': '2',
                '#': '3', '-': '3',
                '$': '4', 'ภ': '4',
                '%': '5', 'ถ': '5',
                '^': '6', 'ุ': '6',
                '&': '7', 'ึ': '7',
                '*': '8', 'ค': '8',
                '(': '9', 'ต': '9'
            }

            if char in digit_map:
                self.on_number_key(digit_map[char])
                return "break"

            if 96 <= code <= 105:
                self.on_number_key(str(code - 96))
                return "break"
            if 48 <= code <= 57:
                self.on_number_key(str(code - 48))
                return "break"

    # =========================================================================
    # Mouse Gestures
    # =========================================================================
    def on_canvas_press(self, event):
        x, y = self.canvas_to_orig(event.x, event.y)
        self.drag_start = (x, y)
        self.clear_typing_buffer()
        curr_time = time.time()

        if self.pending_right_click:
            clicked_idx = self._find_clicked_box(x, y)
            if clicked_idx is not None:
                self.selected_box_idx = clicked_idx
                self.delete_selected_box()
            self.pending_right_click = False
            return

        self.pending_right_click = False

        if curr_time - self.last_left_click_time < 0.35:
            clicked_idx = self._find_clicked_box(x, y)
            if clicked_idx is None:
                self.prev_image()
                self.last_left_click_time = 0
                return

        self.last_left_click_time = curr_time

        if self.selected_box_idx is not None:
            sb = self.bboxes[self.selected_box_idx]
            x1, y1, x2, y2 = sb[1], sb[2], sb[3], sb[4]
            tol = int(12 / self.render_scale)
            
            if abs(x - x1) < tol and abs(y - y1) < tol: self.drag_mode = 'resize_tl'
            elif abs(x - x2) < tol and abs(y - y1) < tol: self.drag_mode = 'resize_tr'
            elif abs(x - x1) < tol and abs(y - y2) < tol: self.drag_mode = 'resize_bl'
            elif abs(x - x2) < tol and abs(y - y2) < tol: self.drag_mode = 'resize_br'

            if self.drag_mode:
                self.initial_bbox = list(sb)
                return

        clicked_idx = self._find_clicked_box(x, y)
        if clicked_idx is not None:
            self.selected_box_idx = clicked_idx
            self.drag_mode = 'move'
            self.initial_bbox = list(self.bboxes[clicked_idx])
            self.cb_classes.current(self.bboxes[clicked_idx][0])
        else:
            self.selected_box_idx = None
            self.drag_mode = 'create'

        self.render()

    def on_right_click_start(self, event):
        self.drag_start = (event.x, event.y)
        curr_time = time.time()
        x, y = self.canvas_to_orig(event.x, event.y)

        if curr_time - self.last_right_click_time < 0.35:
            self.next_image()
            self.last_right_click_time = 0
            self.pending_right_click = False
            return

        self.last_right_click_time = curr_time
        
        clicked_idx = self._find_clicked_box(x, y)
        if clicked_idx is not None:
            self.pending_right_click = True
        else:
            self.pending_right_click = False

    def _find_clicked_box(self, x, y):
        for idx, (cls_id, x1, y1, x2, y2) in enumerate(self.bboxes):
            if self.visible_classes.get(cls_id, True):
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return idx
        return None

    def on_canvas_drag(self, event):
        x, y = self.canvas_to_orig(event.x, event.y)
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        if self.drag_mode == 'move' and self.selected_box_idx is not None:
            init = self.initial_bbox
            w, h = init[3] - init[1], init[4] - init[2]
            nx1 = max(0, min(self.orig_w - w, init[1] + dx))
            ny1 = max(0, min(self.orig_h - h, init[2] + dy))
            self.bboxes[self.selected_box_idx][1:5] = [nx1, ny1, nx1 + w, ny1 + h]

        elif self.drag_mode and self.drag_mode.startswith('resize'):
            init = self.initial_bbox
            b = list(init)
            if 'tl' in self.drag_mode: b[1], b[2] = min(x, b[3]-5), min(y, b[4]-5)
            elif 'tr' in self.drag_mode: b[3], b[2] = max(x, b[1]+5), min(y, b[4]-5)
            elif 'bl' in self.drag_mode: b[1], b[4] = min(x, b[3]-5), max(y, b[2]+5)
            elif 'br' in self.drag_mode: b[3], b[4] = max(x, b[1]+5), max(y, b[2]+5)
            self.bboxes[self.selected_box_idx][1:5] = b[1:5]

        elif self.drag_mode == 'create':
            x1, y1 = self.drag_start
            cls_id = self.cb_classes.current() if self.cb_classes.current() >= 0 else 0
            temp_bboxes = list(self.bboxes) + [[cls_id, min(x1, x), min(y1, y), max(x1, x), max(y1, y)]]
            self.render_temp(temp_bboxes)
            return

        self.render()

    def on_canvas_release(self, event):
        if self.drag_mode == 'create':
            x, y = self.canvas_to_orig(event.x, event.y)
            x1, y1 = self.drag_start
            if abs(x - x1) > 8 and abs(y - y1) > 8:
                cls_id = self.cb_classes.current() if self.cb_classes.current() >= 0 else 0
                new_box = [cls_id, min(x1, x), min(y1, y), max(x1, x), max(y1, y)]
                self.bboxes.append(new_box)
                self.selected_box_idx = len(self.bboxes) - 1
                self.push_history()

        elif self.drag_mode in ['move', 'resize_tl', 'resize_tr', 'resize_bl', 'resize_br']:
            self.push_history()

        self.drag_mode = None
        self.render()
        self.update_box_list()

    def on_right_click_drag(self, event):
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start = (event.x, event.y)
        self.render()

    # =========================================================================
    # Render Engine
    # =========================================================================
    def render(self):
        if self.cv_img is None:
            return

        disp_img = self.cv_img.copy()

        for idx, (cls_id, x1, y1, x2, y2) in enumerate(self.bboxes):
            if not self.visible_classes.get(cls_id, True):
                continue

            rgb_color = self.get_class_color(cls_id)
            bgr_color = rgb_color[::-1]
            
            is_sel = (idx == self.selected_box_idx)
            thickness = 3 if is_sel else 2

            cv2.rectangle(disp_img, (x1, y1), (x2, y2), bgr_color, thickness)
            
            if is_sel:
                handle_radius = max(4, int(6 / self.render_scale))
                for hx, hy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                    cv2.circle(disp_img, (hx, hy), handle_radius, (255, 255, 255), -1)

            c_name = self.classes[cls_id] if cls_id < len(self.classes) else f"Class {cls_id + 1}"
            lbl_str = f" [{cls_id + 1}] {c_name} "

            font_scale = 0.55
            font_thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(lbl_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
            
            label_y1 = max(y1 - text_h - 8, 0)
            label_y2 = label_y1 + text_h + 8
            label_x2 = x1 + text_w + 4

            cv2.rectangle(disp_img, (x1, label_y1), (label_x2, label_y2), (0, 0, 0), -1)
            cv2.rectangle(disp_img, (x1, label_y1), (label_x2, label_y2), bgr_color, 1)
            cv2.putText(disp_img, lbl_str, (x1 + 2, label_y2 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600

        scale_base = min(cw / self.orig_w, ch / self.orig_h)
        self.render_scale = scale_base * self.zoom_level

        new_w = max(1, int(self.orig_w * self.render_scale))
        new_h = max(1, int(self.orig_h * self.render_scale))

        resized = cv2.resize(disp_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb_img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        self.tk_image = ImageTk.PhotoImage(Image.fromarray(rgb_img))
        self.canvas.delete("all")
        
        self.offset_x = (cw - new_w) // 2 + self.pan_x
        self.offset_y = (ch - new_h) // 2 + self.pan_y

        self.canvas.create_image(self.offset_x + new_w // 2, self.offset_y + new_h // 2, image=self.tk_image, anchor="center")

    # =========================================================================
    # Dataset Engine
    # =========================================================================
    def load_dataset(self):
        dir_path = filedialog.askdirectory(title="Select Auto-labeled Output Directory")
        if not dir_path:
            return

        self.src_dir = os.path.abspath(dir_path)
        
        self.img_dir = os.path.join(self.src_dir, "images") if os.path.exists(os.path.join(self.src_dir, "images")) else self.src_dir
        self.lbl_dir = os.path.join(self.src_dir, "labels") if os.path.exists(os.path.join(self.src_dir, "labels")) else self.src_dir
        self.meta_file = os.path.join(self.src_dir, ".pk_annotation_meta.json")

        if os.path.exists(self.meta_file):
            with open(self.meta_file, "r", encoding="utf-8") as f:
                self.meta_data = json.load(f)
        else:
            self.meta_data = {}

        self.cls_file = os.path.join(self.src_dir, "classes.txt")
        if not os.path.exists(self.cls_file):
            self.cls_file = os.path.join(self.lbl_dir, "classes.txt")

        if os.path.exists(self.cls_file):
            with open(self.cls_file, "r", encoding="utf-8") as f:
                self.classes = [line.strip() for line in f if line.strip()]
        elif self.auto_model is not None:
            # ยังไม่มี classes.txt แต่โหลดโมเดลไว้แล้ว -> ใช้ชื่อ class จริงจากโมเดล
            # แทนชื่อปลอม "Class 1".."Class 10" (ไม่งั้น Auto-Label จะ map ชื่อไม่เจอ
            # แล้วข้ามทุกกรอบไปหมด เพราะชื่อไม่ตรงกันเลยสักตัว)
            model_names = self.auto_model.names
            self.classes = [model_names[i] for i in range(len(model_names))]
            self._write_classes_file()
        else:
            self.classes = [f"Class {i + 1}" for i in range(10)]

        self.classes = sorted(list(set(self.classes)), key=lambda x: x.lower())
        
        display_classes = [f"[{i + 1}] {c}" for i, c in enumerate(self.classes)]
        self.cb_classes["values"] = display_classes
        if self.classes:
            self.cb_classes.current(0)

        exts = (".jpg", ".jpeg", ".png", ".bmp")
        self.image_files = sorted([f for f in os.listdir(self.img_dir) if f.lower().endswith(exts)])
        
        if not self.image_files:
            messagebox.showerror("Error", "No valid image files found!")
            return

        self.apply_image_filters()
        self.calculate_global_statistics()

    # =========================================================================
    # Auto-Label Engine (YOLO) — เพิ่มใหม่: ทำทีละรูปหรือทั้งโฟลเดอร์
    # =========================================================================
    def load_yolo_model(self) -> None:
        path = filedialog.askopenfilename(title="เลือกไฟล์โมเดล YOLO (best.pt)", filetypes=[("PyTorch Model", "*.pt")])
        if not path:
            return
        try:
            from ultralytics import YOLO
            self.model_path = path
            self.auto_model = YOLO(path)

            # ถ้าเปิด dataset ไว้แล้วแต่ยังไม่มี classes.txt จริง (ใช้ชื่อปลอม
            # "Class 1".."Class 10" อยู่) ให้ sync เป็นชื่อจริงจากโมเดลทันที ไม่งั้น
            # Auto-Label จะ map ชื่อไม่เจอแล้วข้ามทุกกรอบไปหมด
            if self.src_dir and (not self.cls_file or not os.path.exists(self.cls_file)):
                model_names = self.auto_model.names
                self.classes = [model_names[i] for i in range(len(model_names))]
                self._write_classes_file()
                display_classes = [f"[{i + 1}] {c}" for i, c in enumerate(self.classes)]
                self.cb_classes["values"] = display_classes
                if self.classes:
                    self.cb_classes.current(0)

            messagebox.showinfo("โหลดโมเดลสำเร็จ", f"โหลดโมเดลสำเร็จ:\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("โหลดโมเดลไม่สำเร็จ", f"เกิดข้อผิดพลาด: {e}")

    def _write_classes_file(self) -> None:
        """เขียน classes.txt ลงในโฟลเดอร์ dataset จากชื่อ class ที่มีอยู่ตอนนี้ใน
        self.classes (ไม่ว่าจะมาจากไฟล์เดิมหรือจากโมเดล) ให้ครั้งต่อไปเปิดโฟลเดอร์
        เดิม จะอ่านชื่อจริงได้เลยไม่ต้องพึ่งโมเดลอีก"""
        if not self.src_dir:
            return
        try:
            target = os.path.join(self.src_dir, "classes.txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write("\n".join(self.classes))
            self.cls_file = target
        except Exception:
            pass

    def _map_model_result_to_bboxes(self, result):
        """แปลงผลลัพธ์จาก model.predict() เป็น self.bboxes (pixel x1,y1,x2,y2) โดย
        map ชื่อ class จากโมเดล -> index ใน self.classes (เรียงตามตัวอักษร ไม่ใช่
        index ดิบของโมเดล) ถ้าเจอ class ที่ไม่มีใน self.classes จะข้ามไป (แจ้งเตือน)"""
        model_names = self.auto_model.names
        new_bboxes = []
        skipped_classes = set()
        for box in result.boxes:
            cls_name = model_names[int(box.cls.item())]
            if cls_name not in self.classes:
                skipped_classes.add(cls_name)
                continue
            cls_id = self.classes.index(cls_name)
            cx, cy, w, h = box.xywhn[0].tolist()
            x1 = int((cx - w / 2) * self.orig_w)
            y1 = int((cy - h / 2) * self.orig_h)
            x2 = int((cx + w / 2) * self.orig_w)
            y2 = int((cy + h / 2) * self.orig_h)
            new_bboxes.append([cls_id, x1, y1, x2, y2])
        return new_bboxes, skipped_classes

    def auto_label_current_image(self) -> None:
        if self.auto_model is None:
            self.load_yolo_model()
            if self.auto_model is None:
                return
        if not self.filtered_images:
            messagebox.showwarning("ยังไม่ได้เปิด Dataset", "กรุณาเปิดโฟลเดอร์ dataset ก่อน")
            return

        img_name = self.filtered_images[self.current_idx]
        img_path = os.path.join(self.img_dir, img_name)
        results = self.auto_model.predict(source=img_path, conf=self.conf_threshold, imgsz=self.imgsz, verbose=False)
        new_bboxes, skipped = self._map_model_result_to_bboxes(results[0])

        self.bboxes = new_bboxes
        self.selected_box_idx = None
        self.push_history()
        self.render()
        self.update_box_list()

        msg = f"ตีกรอบอัตโนมัติสำเร็จ! พบวัตถุ {len(new_bboxes)} ชิ้น"
        if skipped:
            msg += f"\n\n(ข้าม class ที่โมเดลรู้จักแต่ไม่มีใน classes.txt: {', '.join(skipped)})"
        messagebox.showinfo("Auto-Label สำเร็จ", msg)

    def run_batch_autolabel(self) -> None:
        if self.auto_model is None:
            self.load_yolo_model()
            if self.auto_model is None:
                return
        if not self.image_files:
            messagebox.showwarning("ยังไม่ได้เปิด Dataset", "กรุณาเปิดโฟลเดอร์ dataset ก่อนเริ่ม Batch Auto-Label")
            return

        # หารูปที่ "ยังไม่มี label" เท่านั้น (ไม่ทับรูปที่ตรวจแก้ไปแล้ว)
        to_process = []
        for img_name in self.image_files:
            txt_path = os.path.join(self.lbl_dir, os.path.splitext(img_name)[0] + ".txt")
            if not os.path.exists(txt_path) or os.path.getsize(txt_path) == 0:
                to_process.append(img_name)

        if not to_process:
            messagebox.showinfo("ไม่มีรูปที่ต้องทำ", "ทุกรูปมี label อยู่แล้ว (Batch Auto-Label ข้ามรูปที่มี label อยู่แล้วเสมอ)")
            return

        if not messagebox.askyesno(
            "ยืนยัน Batch Auto-Label",
            f"พบ {len(to_process)} รูปที่ยังไม่มี label (จากทั้งหมด {len(self.image_files)} รูป)\n"
            f"ต้องการให้ AI ตีกรอบอัตโนมัติเฉพาะรูปเหล่านี้หรือไม่?\n"
            f"(รูปที่มี label อยู่แล้วจะไม่ถูกแตะต้อง)",
        ):
            return

        self._batch_running = True

        def job():
            done_count = 0
            error_count = 0
            skipped_classes_all = set()
            for idx, img_name in enumerate(to_process, start=1):
                if not self._batch_running:
                    break
                try:
                    img_path = os.path.join(self.img_dir, img_name)
                    img_data = np.fromfile(img_path, dtype=np.uint8)
                    cv_img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    h_px, w_px = cv_img.shape[:2]

                    results = self.auto_model.predict(
                        source=img_path, conf=self.conf_threshold, imgsz=self.imgsz, verbose=False
                    )
                    model_names = self.auto_model.names
                    lines = []
                    for box in results[0].boxes:
                        cls_name = model_names[int(box.cls.item())]
                        if cls_name not in self.classes:
                            skipped_classes_all.add(cls_name)
                            continue
                        cls_id = self.classes.index(cls_name)
                        cx, cy, w, h = box.xywhn[0].tolist()
                        lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

                    txt_path = os.path.join(self.lbl_dir, os.path.splitext(img_name)[0] + ".txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    done_count += 1
                except Exception:
                    error_count += 1

                if idx % 5 == 0 or idx == len(to_process):
                    self.after(0, lambda i=idx: self.lbl_file_info.config(
                        text=f"Batch Auto-Label: {i}/{len(to_process)} รูป..."
                    ))

            self._batch_running = False

            def finish():
                msg = f"Batch Auto-Label เสร็จสิ้น!\nสำเร็จ: {done_count} รูป | ผิดพลาด: {error_count} รูป"
                if skipped_classes_all:
                    msg += f"\n\n(ข้าม class ที่โมเดลรู้จักแต่ไม่มีใน classes.txt: {', '.join(skipped_classes_all)})"
                messagebox.showinfo("Batch เสร็จสิ้น", msg)
                self.apply_image_filters()
                self.calculate_global_statistics()

            self.after(0, finish)

        threading.Thread(target=job, daemon=True).start()

    def load_current_image(self):
        if not self.filtered_images:
            self.canvas.delete("all")
            self.lbl_file_info.config(text="No images match current filter criteria!")
            return

        img_name = self.filtered_images[self.current_idx]
        img_path = os.path.join(self.img_dir, img_name)
        
        img_data = np.fromfile(img_path, dtype=np.uint8)
        self.cv_img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        self.orig_h, self.orig_w, _ = self.cv_img.shape

        txt_name = os.path.splitext(img_name)[0] + ".txt"
        txt_path = os.path.join(self.lbl_dir, txt_name)

        self.bboxes = []
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        cx, cy, w, h = map(float, parts[1:5])
                        
                        x1 = int((cx - w / 2) * self.orig_w)
                        y1 = int((cy - h / 2) * self.orig_h)
                        x2 = int((cx + w / 2) * self.orig_w)
                        y2 = int((cy + h / 2) * self.orig_h)
                        self.bboxes.append([cls_id, x1, y1, x2, y2])

        self.selected_box_idx = None
        self.reset_zoom()
        self.clear_typing_buffer()
        self.init_history()
        self.render()
        self.update_box_list()
        
        is_rev = self.meta_data.get(img_name, {}).get("reviewed", False)
        rev_str = "✓ Reviewed" if is_rev else "⚠ Unreviewed"
        
        self.lbl_file_info.config(text=f"[{self.current_idx + 1}/{len(self.filtered_images)}] {img_name} ({rev_str})")

    def calculate_global_statistics(self):
        if not self.image_files:
            return

        global_cls_counts = {i: 0 for i in range(len(self.classes))}
        total_boxes = 0

        for img_name in self.image_files:
            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = os.path.join(self.lbl_dir, txt_name)
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            cls_id = int(parts[0])
                            global_cls_counts[cls_id] = global_cls_counts.get(cls_id, 0) + 1
                            total_boxes += 1

        stats_lines = [
            f"Total Dataset Images: {len(self.image_files)}",
            f"Total Dataset Boxes:  {total_boxes}",
            "=" * 30,
            "Class Breakdown (Whole Folder):"
        ]
        for i, c_name in enumerate(self.classes):
            count = global_cls_counts.get(i, 0)
            stats_lines.append(f"  [{i + 1}] {c_name}: {count}")

        self.global_stats_text.config(state="normal")
        self.global_stats_text.delete("1.0", tk.END)
        self.global_stats_text.insert(tk.END, "\n".join(stats_lines))
        self.global_stats_text.config(state="disabled")

    def apply_class_change(self):
        if self.selected_box_idx is not None and self.selected_box_idx < len(self.bboxes):
            cls_id = self.cb_classes.current()
            if cls_id >= 0:
                self.bboxes[self.selected_box_idx][0] = cls_id
                self.push_history()
                self.render()
                self.update_box_list()

    def canvas_to_orig(self, cx, cy):
        ox = int((cx - self.offset_x) / self.render_scale)
        oy = int((cy - self.offset_y) / self.render_scale)
        return max(0, min(ox, self.orig_w)), max(0, min(oy, self.orig_h))

    def render_temp(self, temp_bboxes):
        curr_bboxes = self.bboxes
        self.bboxes = temp_bboxes
        self.render()
        self.bboxes = curr_bboxes

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.lbl_zoom.config(text="100%")

    def change_zoom(self, delta):
        self.zoom_level = max(0.25, min(8.0, self.zoom_level + delta))
        self.lbl_zoom.config(text=f"{int(self.zoom_level * 100)}%")
        self.render()

    def on_mouse_wheel(self, event):
        delta = 0.15 if event.delta > 0 else -0.15
        self.change_zoom(delta)

    def init_history(self):
        self.history = [[list(b) for b in self.bboxes]]
        self.history_idx = 0

    def push_history(self):
        self.history = self.history[:self.history_idx + 1]
        self.history.append([list(b) for b in self.bboxes])
        self.history_idx += 1

    def undo(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            self.bboxes = [list(b) for b in self.history[self.history_idx]]
            self.render()
            self.update_box_list()

    def redo(self):
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.bboxes = [list(b) for b in self.history[self.history_idx]]
            self.render()
            self.update_box_list()

    def save_current(self):
        if not self.filtered_images:
            return

        img_name = self.filtered_images[self.current_idx]
        txt_name = os.path.splitext(img_name)[0] + ".txt"
        txt_path = os.path.join(self.lbl_dir, txt_name)

        lines = []
        for cls_id, x1, y1, x2, y2 in self.bboxes:
            bw = (x2 - x1) / self.orig_w
            bh = (y2 - y1) / self.orig_h
            cx = (x1 + (x2 - x1) / 2) / self.orig_w
            cy = (y1 + (y2 - y1) / 2) / self.orig_h
            lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        if img_name not in self.meta_data:
            self.meta_data[img_name] = {}
        
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.meta_data, f, indent=2)

        self.calculate_global_statistics()

    def save_all(self):
        self.save_current()
        messagebox.showinfo("Save All", "Saved labels directly to dataset folder!")

    def prev_image(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_current_image()

    def next_image(self):
        if not self.filtered_images:
            return
        
        img_name = self.filtered_images[self.current_idx]
        if img_name not in self.meta_data:
            self.meta_data[img_name] = {}
        
        self.meta_data[img_name]["reviewed"] = True

        if self.current_idx < len(self.filtered_images) - 1:
            self.current_idx += 1
            self.load_current_image()
        else:
            self.load_current_image()

    def delete_selected_box(self):
        if self.selected_box_idx is not None and self.selected_box_idx < len(self.bboxes):
            del self.bboxes[self.selected_box_idx]
            self.selected_box_idx = None
            self.push_history()
            self.render()
            self.update_box_list()

    def update_stats(self):
        total_images = len(self.filtered_images)
        reviewed_images = sum(1 for v in self.meta_data.values() if v.get("reviewed", False))
        self.lbl_progress.config(text=f"Filtered Images: {total_images} | Reviewed: {reviewed_images}")

    def on_number_key(self, digit):
        self.class_input_buffer += digit
        self.update_typing_feedback()

    def on_key_backspace(self):
        if self.class_input_buffer:
            self.class_input_buffer = self.class_input_buffer[:-1]
            self.update_typing_feedback()
        else:
            self.delete_selected_box()

    def clear_typing_buffer(self):
        self.class_input_buffer = ""
        self.update_typing_feedback()

    def update_typing_feedback(self):
        if self.class_input_buffer:
            try:
                user_num = int(self.class_input_buffer)
                target_idx = user_num - 1
                
                if 0 <= target_idx < len(self.classes):
                    c_name = self.classes[target_idx]
                    self.lbl_typing_feedback.config(text=f"Typing: [{user_num}] ➔ {c_name} (Press ENTER)", foreground=COLORS["warning"])
                else:
                    self.lbl_typing_feedback.config(text=f"Typing: [{user_num}] (Out of range!)", foreground=COLORS["danger"])
            except ValueError:
                pass
        else:
            self.lbl_typing_feedback.config(text="Type Class ID + Enter to apply", foreground=COLORS["accent"])

    def on_key_enter(self):
        if self.class_input_buffer:
            try:
                user_num = int(self.class_input_buffer)
                target_idx = user_num - 1
                
                if 0 <= target_idx < len(self.classes):
                    self.cb_classes.current(target_idx)
                    if self.selected_box_idx is not None and self.selected_box_idx < len(self.bboxes):
                        self.bboxes[self.selected_box_idx][0] = target_idx
                        self.push_history()
                        self.render()
                        self.update_box_list()
            except ValueError:
                pass
            
            self.clear_typing_buffer()
