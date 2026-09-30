"""
=========================================================================
PK Studio - Tab: Zone Editor

Draw polygon zones on a chosen video frame (entry / exit / conflict /
detection zones) and export them as JSON so a downstream tracking script
can test whether a detected object's position falls inside a given zone
on each frame (e.g. for PET / Gap Acceptance analysis at access points).

Workflow:
  1. Open a video.
  2. Scrub to a clear reference frame (scrubber + frame step buttons).
  3. Left-click on the canvas to place polygon vertices (>= 3 points).
  4. Right-click removes the last placed vertex while drawing.
  5. Name the zone, pick/type a zone type, then "Finish Zone" (or
     double-click on the canvas) to save it into the zone list.
  6. Save all zones to a .json file (pixel + normalized coordinates).
=========================================================================
"""

import json
import uuid
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk

from pk_studio.theme import COLORS

VIDEO_FILETYPES = [
    ("Video files", "*.mp4 *.avi *.mov *.mkv *.MP4 *.AVI *.MOV *.MKV"),
    ("All files", "*.*"),
]

ZONE_TYPE_PRESETS = ["entry", "exit", "conflict", "detection", "other"]

# BGR palette (cv2 drawing order) — cycled per zone so each new zone gets a
# visually distinct, stable color that is also saved into the zone's data.
ZONE_PALETTE_BGR = [
    (0, 200, 0),      # green
    (0, 0, 230),      # red
    (0, 150, 255),    # orange
    (230, 120, 0),    # blue
    (200, 0, 200),    # magenta
    (0, 210, 210),    # yellow-ish cyan
    (255, 0, 120),    # purple-pink
    (0, 255, 255),    # yellow
    (150, 150, 150),  # gray
    (255, 255, 0),    # cyan
]


class ZoneEditorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=0)

        # Video state
        self.video_path = ""
        self.cap = None
        self.fps = 0.0
        self.total_frames = 0
        self.orig_w, self.orig_h = 1, 1
        self.current_frame_idx = 0
        self.cv_frame = None

        # Zone state
        self.zones = []            # list of dicts (see _finish_zone)
        self.current_points = []   # in-progress polygon, orig pixel coords
        self.selected_zone_idx = None
        self.zones_file = ""

        # Canvas render state
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.offset_x = 0
        self.offset_y = 0
        self.render_scale = 1.0
        self.tk_image = None

        self._updating_scrub = False

        self._build_ui()

    # =====================================================================
    # UI
    # =====================================================================
    def _build_ui(self):
        top_bar = ttk.Frame(self, padding=(12, 10, 12, 4))
        top_bar.pack(fill="x")

        ttk.Button(top_bar, text="📂 Open Video", command=self._pick_video).pack(side="left")
        self.lbl_video_path = ttk.Label(top_bar, text="No video loaded", foreground=COLORS["text_muted"])
        self.lbl_video_path.pack(side="left", padx=10)

        self.lbl_frame_info = ttk.Label(top_bar, text="", foreground=COLORS["text_muted"])
        self.lbl_frame_info.pack(side="right")

        # -----------------------------------------------------------
        # Frame scrubber
        # -----------------------------------------------------------
        scrub_bar = ttk.Frame(self, padding=(12, 0, 12, 6))
        scrub_bar.pack(fill="x")

        ttk.Button(scrub_bar, text="|◀", width=3, command=lambda: self._step_frame(-1)).pack(side="left")
        self.scrubber = ttk.Scale(
            scrub_bar, from_=0, to=0, orient="horizontal", command=self._on_scrub_drag
        )
        self.scrubber.pack(side="left", fill="x", expand=True, padx=6)
        self.scrubber.bind("<ButtonRelease-1>", self._on_scrub_release)
        ttk.Button(scrub_bar, text="▶|", width=3, command=lambda: self._step_frame(1)).pack(side="left")

        ttk.Button(scrub_bar, text="◀◀ 1s", command=self._step_back_1s).pack(side="left", padx=(10, 2))
        ttk.Button(scrub_bar, text="1s ▶▶", command=self._step_fwd_1s).pack(side="left", padx=(2, 10))

        ttk.Label(scrub_bar, text="Go to frame:").pack(side="left")
        self.entry_jump_frame = ttk.Entry(scrub_bar, width=8)
        self.entry_jump_frame.pack(side="left", padx=4)
        self.entry_jump_frame.bind("<Return>", lambda e: self._on_jump_frame())
        ttk.Button(scrub_bar, text="Go", command=self._on_jump_frame).pack(side="left")

        # -----------------------------------------------------------
        # Body: canvas + side panel
        # -----------------------------------------------------------
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        canvas_frame = tk.Frame(body, bg="#1A1A1A")
        canvas_frame.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=(0, 10))

        self.canvas = tk.Canvas(canvas_frame, bg="#1A1A1A", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.render())
        self.canvas.bind("<Button-1>", self._on_canvas_left_click)
        self.canvas.bind("<Double-Button-1>", lambda e: self._finish_zone())
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._change_zoom(0.15))   # Linux scroll up
        self.canvas.bind("<Button-5>", lambda e: self._change_zoom(-0.15))  # Linux scroll down

        side = ttk.Frame(body, width=320, padding=(6, 0, 12, 10))
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        instr = ttk.LabelFrame(side, text="How to draw a zone")
        instr.pack(fill="x", pady=(0, 8))
        ttk.Label(
            instr,
            wraplength=290,
            justify="left",
            text=(
                "1) Left-click to place polygon points (need 3+)\n"
                "2) Right-click to undo the last point\n"
                "3) Set a name + type below\n"
                "4) Double-click the canvas, or press \"Finish Zone\", to save it"
            ),
        ).pack(padx=8, pady=8, anchor="w")

        new_zone_box = ttk.LabelFrame(side, text="New zone")
        new_zone_box.pack(fill="x", pady=(0, 8))

        ttk.Label(new_zone_box, text="Zone name:").pack(anchor="w", padx=8, pady=(8, 0))
        self.entry_zone_name = ttk.Entry(new_zone_box)
        self.entry_zone_name.pack(fill="x", padx=8, pady=(2, 6))

        ttk.Label(new_zone_box, text="Zone type:").pack(anchor="w", padx=8)
        self.cb_zone_type = ttk.Combobox(new_zone_box, values=ZONE_TYPE_PRESETS, state="normal")
        self.cb_zone_type.set(ZONE_TYPE_PRESETS[0])
        self.cb_zone_type.pack(fill="x", padx=8, pady=(2, 8))

        btn_row = ttk.Frame(new_zone_box)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="✔ Finish Zone", command=self._finish_zone).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btn_row, text="✕ Cancel Draw", style="Secondary.TButton", command=self._cancel_draw).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.lbl_point_count = ttk.Label(new_zone_box, text="Points placed: 0", foreground=COLORS["text_muted"])
        self.lbl_point_count.pack(anchor="w", padx=8, pady=(0, 8))

        list_box = ttk.LabelFrame(side, text="Zones")
        list_box.pack(fill="both", expand=True, pady=(0, 8))

        self.tree_zones = ttk.Treeview(
            list_box, columns=("type", "pts", "area"), show="tree headings", height=8, selectmode="browse"
        )
        self.tree_zones.heading("#0", text="Name")
        self.tree_zones.heading("type", text="Type")
        self.tree_zones.heading("pts", text="Pts")
        self.tree_zones.heading("area", text="Area (px\u00b2)")
        self.tree_zones.column("#0", width=120)
        self.tree_zones.column("type", width=70)
        self.tree_zones.column("pts", width=30, anchor="center")
        self.tree_zones.column("area", width=80, anchor="e")
        self.tree_zones.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree_zones.bind("<<TreeviewSelect>>", self._on_zone_select)

        zone_btn_row = ttk.Frame(list_box)
        zone_btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(zone_btn_row, text="Rename", style="Secondary.TButton", command=self._rename_selected_zone).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(zone_btn_row, text="Delete", style="Secondary.TButton", command=self._delete_selected_zone).pack(side="left", expand=True, fill="x", padx=(3, 0))

        io_box = ttk.LabelFrame(side, text="Save / Load / Export")
        io_box.pack(fill="x")
        io_row = ttk.Frame(io_box)
        io_row.pack(fill="x", padx=8, pady=8)
        ttk.Button(io_row, text="💾 Save Zones", command=self._save_zones).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(io_row, text="📂 Load Zones", style="Secondary.TButton", command=self._load_zones).pack(side="left", expand=True, fill="x", padx=(3, 0))
        ttk.Button(io_box, text="🐍 View / Export as Python", style="Secondary.TButton", command=self._show_code_preview).pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(io_box, text="🗑 Clear All Zones", style="Secondary.TButton", command=self._clear_all_zones).pack(fill="x", padx=8, pady=(0, 8))

        self.status_label = ttk.Label(self, text="Open a video to begin.", padding=(12, 4), foreground=COLORS["text_muted"])
        self.status_label.pack(fill="x", side="bottom")

    # =====================================================================
    # Video loading / navigation
    # =====================================================================
    def _pick_video(self):
        path = filedialog.askopenfilename(title="Select a video", filetypes=VIDEO_FILETYPES)
        if not path:
            return
        if self.zones:
            if not messagebox.askyesno(
                "Open new video",
                "Opening a new video will clear the zones you've drawn so far "
                "(save them first if you want to keep them). Continue?",
            ):
                return
        self._load_video(path)

    def _load_video(self, path):
        if self.cap is not None:
            self.cap.release()

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror("Error", f"Could not open video:\n{path}")
            return

        self.cap = cap
        self.video_path = path
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        self.total_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1
        self.orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1

        self.zones = []
        self.current_points = []
        self.selected_zone_idx = None
        self._refresh_zone_list()

        self.scrubber.config(from_=0, to=max(0, self.total_frames - 1))
        self.reset_zoom()

        self.lbl_video_path.config(text=Path(path).name, foreground=COLORS["text_dark"])
        self._seek_and_load_frame(0)
        self.status_label.config(text=f"Loaded video: {path}  ({self.orig_w}x{self.orig_h}, {self.total_frames} frames)")

    def _seek_and_load_frame(self, idx):
        if self.cap is None:
            return
        idx = max(0, min(idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showwarning("Warning", f"Could not read frame {idx}.")
            return

        self.cv_frame = frame
        self.current_frame_idx = idx

        self._updating_scrub = True
        self.scrubber.set(idx)
        self._updating_scrub = False

        t_str = f"  |  t={idx / self.fps:.2f}s" if self.fps > 0 else ""
        self.lbl_frame_info.config(text=f"Frame {idx + 1}/{self.total_frames}{t_str}")
        self.render()

    def _step_frame(self, delta):
        if self.cap is None:
            return
        self._seek_and_load_frame(self.current_frame_idx + delta)

    def _step_back_1s(self):
        step = int(self.fps) if self.fps > 0 else 30
        self._step_frame(-step)

    def _step_fwd_1s(self):
        step = int(self.fps) if self.fps > 0 else 30
        self._step_frame(step)

    def _on_scrub_drag(self, value):
        # Lightweight preview while dragging — avoid reading a video frame on
        # every pixel of drag movement; the actual seek happens on release.
        if self._updating_scrub or self.cap is None:
            return
        idx = int(float(value))
        t_str = f"  |  t={idx / self.fps:.2f}s" if self.fps > 0 else ""
        self.lbl_frame_info.config(text=f"Frame {idx + 1}/{self.total_frames}{t_str} (dragging...)")

    def _on_scrub_release(self, _event):
        if self.cap is None:
            return
        idx = int(float(self.scrubber.get()))
        self._seek_and_load_frame(idx)

    def _on_jump_frame(self):
        if self.cap is None:
            return
        val = self.entry_jump_frame.get().strip()
        if not val.isdigit():
            messagebox.showwarning("Warning", "Enter a frame number.")
            return
        target = int(val) - 1  # shown as 1-based to match the frame info label
        if 0 <= target < self.total_frames:
            self._seek_and_load_frame(target)
            self.entry_jump_frame.delete(0, tk.END)
        else:
            messagebox.showerror("Error", f"Valid range: 1 to {self.total_frames}.")

    # =====================================================================
    # Zoom
    # =====================================================================
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

    def _change_zoom(self, delta):
        self.zoom_level = max(0.25, min(8.0, self.zoom_level + delta))
        self.render()

    def _on_mouse_wheel(self, event):
        delta = 0.15 if event.delta > 0 else -0.15
        self._change_zoom(delta)

    def canvas_to_orig(self, cx, cy):
        ox = int((cx - self.offset_x) / self.render_scale)
        oy = int((cy - self.offset_y) / self.render_scale)
        return max(0, min(ox, self.orig_w)), max(0, min(oy, self.orig_h))

    @staticmethod
    def _polygon_area(points):
        """Shoelace formula — area in px^2 for a simple (non-self-intersecting) polygon."""
        n = len(points)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2.0

    # =====================================================================
    # Drawing interactions
    # =====================================================================
    def _on_canvas_left_click(self, event):
        if self.cv_frame is None:
            return
        x, y = self.canvas_to_orig(event.x, event.y)
        self.current_points.append((x, y))
        self.lbl_point_count.config(text=f"Points placed: {len(self.current_points)}")
        self.render()

    def _on_canvas_right_click(self, _event):
        if self.current_points:
            self.current_points.pop()
            self.lbl_point_count.config(text=f"Points placed: {len(self.current_points)}")
            self.render()

    def _cancel_draw(self):
        self.current_points = []
        self.lbl_point_count.config(text="Points placed: 0")
        self.render()

    def _finish_zone(self):
        if self.cv_frame is None:
            return
        if len(self.current_points) < 3:
            messagebox.showwarning("Not enough points", "A zone needs at least 3 points.")
            return

        name = self.entry_zone_name.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please name the zone before finishing it.")
            return

        ztype = self.cb_zone_type.get().strip() or "other"
        color = ZONE_PALETTE_BGR[len(self.zones) % len(ZONE_PALETTE_BGR)]
        area_px = self._polygon_area(self.current_points)

        zone = {
            "id": f"zone_{uuid.uuid4().hex[:8]}",
            "name": name,
            "type": ztype,
            "points": [[int(x), int(y)] for x, y in self.current_points],
            "area_px": round(area_px, 2),
            "color_bgr": list(color),
            "reference_frame_index": self.current_frame_idx,
        }
        self.zones.append(zone)
        self.current_points = []

        self.entry_zone_name.delete(0, tk.END)
        self.lbl_point_count.config(text="Points placed: 0")
        self._refresh_zone_list()
        self.render()
        self.status_label.config(
            text=f"Added zone '{name}' ({ztype}) — {len(zone['points'])} points, area \u2248 {area_px:,.0f} px\u00b2."
        )

    # =====================================================================
    # Zone list management
    # =====================================================================
    def _refresh_zone_list(self):
        self.tree_zones.delete(*self.tree_zones.get_children())
        for i, z in enumerate(self.zones):
            area = z.get("area_px")
            if area is None:
                area = self._polygon_area(z["points"])
                z["area_px"] = round(area, 2)
            self.tree_zones.insert(
                "", "end", iid=str(i), text=z["name"],
                values=(z["type"], len(z["points"]), f"{z['area_px']:,.0f}"),
            )

    def _on_zone_select(self, _event):
        sel = self.tree_zones.selection()
        self.selected_zone_idx = int(sel[0]) if sel else None
        self.render()

    def _rename_selected_zone(self):
        if self.selected_zone_idx is None:
            messagebox.showinfo("No selection", "Select a zone from the list first.")
            return
        zone = self.zones[self.selected_zone_idx]
        new_name = simpledialog.askstring("Rename zone", "New name:", initialvalue=zone["name"])
        if new_name and new_name.strip():
            zone["name"] = new_name.strip()
            self._refresh_zone_list()
            self.render()

    def _delete_selected_zone(self):
        if self.selected_zone_idx is None:
            messagebox.showinfo("No selection", "Select a zone from the list first.")
            return
        zone = self.zones[self.selected_zone_idx]
        if messagebox.askyesno("Delete zone", f"Delete zone '{zone['name']}'?"):
            del self.zones[self.selected_zone_idx]
            self.selected_zone_idx = None
            self._refresh_zone_list()
            self.render()

    def _clear_all_zones(self):
        if not self.zones:
            return
        if messagebox.askyesno("Clear all zones", "Delete every zone? This cannot be undone."):
            self.zones = []
            self.selected_zone_idx = None
            self._refresh_zone_list()
            self.render()

    # =====================================================================
    # Save / Load
    # =====================================================================
    def _save_zones(self):
        if not self.zones:
            messagebox.showwarning("Nothing to save", "No zones have been drawn yet.")
            return

        default_name = f"{Path(self.video_path).stem}_zones.json" if self.video_path else "zones.json"
        path = filedialog.asksaveasfilename(
            title="Save zones",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("Zone JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        zones_out = []
        for z in self.zones:
            pts = z["points"]
            pts_norm = [[round(x / self.orig_w, 6), round(y / self.orig_h, 6)] for x, y in pts]
            zones_out.append({
                "id": z["id"],
                "name": z["name"],
                "type": z["type"],
                "points": pts,
                "points_norm": pts_norm,
                "area_px": z.get("area_px", self._polygon_area(pts)),
                "color_bgr": z.get("color_bgr"),
                "reference_frame_index": z.get("reference_frame_index"),
            })

        data = {
            "video_path": self.video_path,
            "frame_width": self.orig_w,
            "frame_height": self.orig_h,
            "zones": zones_out,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not save zones:\n{exc}")
            return

        self.zones_file = path
        self.status_label.config(text=f"Saved {len(self.zones)} zone(s) to: {path}")
        messagebox.showinfo("Saved", f"Saved {len(self.zones)} zone(s) to:\n{path}")

    def _load_zones(self):
        path = filedialog.askopenfilename(title="Load zones", filetypes=[("Zone JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not read zones file:\n{exc}")
            return

        if self.cv_frame is not None:
            fw, fh = data.get("frame_width"), data.get("frame_height")
            if fw and fh and (fw != self.orig_w or fh != self.orig_h):
                if not messagebox.askyesno(
                    "Resolution mismatch",
                    f"This zone file was made for a {fw}x{fh} frame, but the current "
                    f"video is {self.orig_w}x{self.orig_h}. Zone positions may not line "
                    f"up. Load anyway?",
                ):
                    return

        loaded_zones = data.get("zones", [])
        for i, z in enumerate(loaded_zones):
            z.setdefault("id", f"zone_{uuid.uuid4().hex[:8]}")
            z.setdefault("color_bgr", list(ZONE_PALETTE_BGR[i % len(ZONE_PALETTE_BGR)]))
            z.setdefault("type", "other")

        self.zones = loaded_zones
        self.zones_file = path
        self.selected_zone_idx = None
        self._refresh_zone_list()
        self.render()
        self.status_label.config(text=f"Loaded {len(self.zones)} zone(s) from: {path}")

    # =====================================================================
    # Export as Python code
    # =====================================================================
    def _generate_python_code(self):
        video_name = Path(self.video_path).name if self.video_path else "(no video loaded)"
        lines = []
        lines.append('"""')
        lines.append("Zone definitions exported from PK Studio - Zone Editor")
        lines.append(f"Video: {video_name}  ({self.orig_w}x{self.orig_h})")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append('"""')
        lines.append("")
        lines.append(f"FRAME_WIDTH = {self.orig_w}")
        lines.append(f"FRAME_HEIGHT = {self.orig_h}")
        lines.append("")
        lines.append("ZONES = [")
        for z in self.zones:
            area = z.get("area_px", self._polygon_area(z["points"]))
            pts_tuple = ", ".join(f"({x}, {y})" for x, y in z["points"])
            lines.append("    {")
            lines.append(f'        "id": {z["id"]!r},')
            lines.append(f'        "name": {z["name"]!r},')
            lines.append(f'        "type": {z["type"]!r},')
            lines.append(f'        "points": [{pts_tuple}],')
            lines.append(f'        "area_px": {area:.2f},')
            lines.append("    },")
        lines.append("]")
        lines.append("")
        lines.append("")
        lines.append("def point_in_zone(x, y, zone):")
        lines.append('    """Return True if point (x, y) — e.g. a bbox centroid — falls')
        lines.append("    inside zone['points']. Coordinates must be in the same pixel")
        lines.append("    space as FRAME_WIDTH x FRAME_HEIGHT (same video resolution).")
        lines.append('    """')
        lines.append("    import cv2")
        lines.append("    import numpy as np")
        lines.append('    pts = np.array(zone["points"], dtype=np.int32)')
        lines.append("    return cv2.pointPolygonTest(pts, (float(x), float(y)), False) >= 0")
        lines.append("")
        lines.append("")
        lines.append("def zone_for_point(x, y, zones=ZONES):")
        lines.append('    """Return the name of the first zone containing (x, y), or None.')
        lines.append("    Use this per-frame with each tracked object's bbox centroid to")
        lines.append("    know which zone (if any) it is currently in — the starting point")
        lines.append('    for behavior detection (entry/exit, dwell time, PET, etc.).')
        lines.append('    """')
        lines.append("    for zone in zones:")
        lines.append("        if point_in_zone(x, y, zone):")
        lines.append('            return zone["name"]')
        lines.append("    return None")
        lines.append("")
        return "\n".join(lines)

    def _show_code_preview(self):
        if not self.zones:
            messagebox.showwarning("Nothing to export", "No zones have been drawn yet.")
            return

        code = self._generate_python_code()

        win = tk.Toplevel(self)
        win.title("Zone code (Python)")
        win.geometry("760x600")

        text = ScrolledText(win, wrap="none", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        text.insert("1.0", code)
        text.config(state="normal")  # keep editable/selectable for easy copying

        btn_row = ttk.Frame(win)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))

        def copy_to_clipboard():
            win.clipboard_clear()
            win.clipboard_append(code)
            status.config(text="Copied to clipboard.")

        def save_as_py():
            default_name = f"{Path(self.video_path).stem}_zones.py" if self.video_path else "zones.py"
            path = filedialog.asksaveasfilename(
                title="Save zone code",
                defaultextension=".py",
                initialfile=default_name,
                filetypes=[("Python file", "*.py"), ("All files", "*.*")],
                parent=win,
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            status.config(text=f"Saved to: {path}")

        ttk.Button(btn_row, text="📋 Copy to Clipboard", command=copy_to_clipboard).pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="💾 Save as .py", style="Secondary.TButton", command=save_as_py).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Close", style="Secondary.TButton", command=win.destroy).pack(side="right")

        status = ttk.Label(win, text=f"{len(self.zones)} zone(s) — ready to copy or save.", foreground=COLORS["text_muted"])
        status.pack(fill="x", padx=8, pady=(0, 8))

    # =====================================================================
    # Render
    # =====================================================================
    def render(self):
        if self.cv_frame is None:
            self.canvas.delete("all")
            return

        disp = self.cv_frame.copy()

        for idx, zone in enumerate(self.zones):
            pts = np.array(zone["points"], dtype=np.int32)
            color = tuple(zone.get("color_bgr") or ZONE_PALETTE_BGR[idx % len(ZONE_PALETTE_BGR)])
            is_sel = (idx == self.selected_zone_idx)

            if is_sel:
                overlay = disp.copy()
                cv2.fillPoly(overlay, [pts], color)
                cv2.addWeighted(overlay, 0.20, disp, 0.80, 0, disp)

            cv2.polylines(disp, [pts], isClosed=True, color=color, thickness=3 if is_sel else 2)
            for (px, py) in zone["points"]:
                cv2.circle(disp, (px, py), 4, color, -1)

            cx = int(np.mean(pts[:, 0]))
            cy = int(np.mean(pts[:, 1]))
            label = f" {zone['name']} ({zone['type']}) "
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(disp, (cx - tw // 2 - 3, cy - th - 6), (cx + tw // 2 + 3, cy + 4), color, -1)
            text_color = (0, 0, 0) if sum(color) > 430 else (255, 255, 255)
            cv2.putText(disp, label, (cx - tw // 2, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 1, cv2.LINE_AA)

        if self.current_points:
            draw_color = (0, 255, 255)  # bright yellow — the polygon currently being drawn
            for i in range(len(self.current_points) - 1):
                cv2.line(disp, self.current_points[i], self.current_points[i + 1], draw_color, 2)
            for i, (px, py) in enumerate(self.current_points):
                radius = 6 if i == 0 else 4
                cv2.circle(disp, (px, py), radius, draw_color, -1)

        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600

        scale_base = min(cw / self.orig_w, ch / self.orig_h)
        self.render_scale = scale_base * self.zoom_level

        new_w = max(1, int(self.orig_w * self.render_scale))
        new_h = max(1, int(self.orig_h * self.render_scale))

        resized = cv2.resize(disp, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb_img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        self.tk_image = ImageTk.PhotoImage(Image.fromarray(rgb_img))
        self.canvas.delete("all")

        self.offset_x = (cw - new_w) // 2 + self.pan_x
        self.offset_y = (ch - new_h) // 2 + self.pan_y

        self.canvas.create_image(self.offset_x + new_w // 2, self.offset_y + new_h // 2, image=self.tk_image, anchor="center")
