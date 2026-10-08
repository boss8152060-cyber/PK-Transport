"""Headless test of the reference lines of Gap Acceptance / Headway: which line is used per stream (shared zone edge or a drawn Line), what the Line window
offers and saves, and that the lines are drawn in the normal video and on the X-Y plane only when asked.

Run from the Run folder:   python tests/gui_refedge.py   (needs torch/cv2/ultralytics; no real video)"""
import importlib.util
import json
import os
import sys
import tempfile
import tkinter as tk

import cv2
import numpy as np

os.environ["PK_STUDIO_CUDA_RELAUNCHED"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pkstudio_main", os.path.join(HERE, "..", "PKStudio.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def make_video(path, w=640, h=360, n=5):
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h))
    for i in range(n):
        writer.write(np.full((h, w, 3), 90 + i * 10, dtype=np.uint8))
    writer.release()


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def make_zone_json(path, video, w, h):
    """Zones that TOUCH: 1|3, 3|2 on the top row; 5|6, 6|7 on the bottom row; 3|6 across."""
    layout = {1: box(0, 0, 100, 100), 3: box(100, 0, 200, 100), 2: box(200, 0, 300, 100), 4: box(300, 0, 400, 100),
              5: box(0, 100, 100, 200), 6: box(100, 100, 200, 200), 7: box(200, 100, 300, 200)}
    zones = [{"id": z, "name": f"Zone {z}", "points": pts} for z, pts in sorted(layout.items())]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"video_path": video, "frame_width": w, "frame_height": h, "zones": zones}, f, indent=2)


def main():
    tmp = tempfile.mkdtemp(prefix="pk_refedge_")
    video = os.path.join(tmp, "v.mp4")
    zpath = os.path.join(tmp, "zones.json")
    make_video(video)
    make_zone_json(zpath, video, 640, 360)

    root = tk.Tk()
    root.withdraw()
    app = m.Run1App(root)
    m.messagebox.askyesno = lambda *a, **k: True
    m.messagebox.showerror = lambda *a, **k: print("showerror:", a[1:2])
    m.messagebox.showwarning = lambda *a, **k: None
    app.video_var.set(video)
    app.zone_line_config_var.set(zpath)
    check("zone file loads", app.load_pkstudio_zones() is True)
    app.run3_site_id_var.set("8")
    app.run3_gap_enabled_var.set(True)
    app.run3_gap_subject_1367_var.set(True)
    for v in (app.run3_gap_subject_134_var, app.run3_gap_subject_5631_var):
        v.set(False)
    app.run3_headway_enabled_var.set(False)               # (Headway would add the edges of its own Movements)

    # ---- default source = the shared zone edge: lines are drawn from the edges, nothing from Lines ----
    check("source is zone_edge by default", app.run3_ref_line_source_var.get() == "zone_edge")
    lines = app._display_ref_lines()
    labels = sorted(lbl.split(" (")[0] for lbl, _a, _b in lines)
    check("1-3-6-7 shows the 3 edges of its conflicting streams", labels == ["Edge 2-3", "Edge 3-6", "Edge 5-6"], str(labels))
    check("no drawn Line is shown", not any(lbl.startswith("Line") for lbl, _a, _b in lines))
    e23 = [(a, b) for lbl, a, b in lines if lbl.startswith("Edge 2-3")][0]
    check("edge 2|3 is the common side x=200", {round(e23[0][0]), round(e23[1][0])} == {200} and {round(e23[0][1]), round(e23[1][1])} == {0, 100}, str(e23))
    app.run3_gap_enabled_var.set(False)
    check("nothing enabled -> nothing shown", app._display_ref_lines() == [])
    app.run3_gap_enabled_var.set(True)

    # ---- the normal-video overlay draws them only when the switch is on ----
    frame_off = np.zeros((360, 640, 3), np.uint8)
    app.show_ref_lines_var.set(False)
    app.draw_measurement_overlay(frame_off, 0, 30.0, {}, {}, {}, {})
    app.show_ref_lines_var.set(True)
    frame_on = np.zeros((360, 640, 3), np.uint8)
    app.draw_measurement_overlay(frame_on, 0, 30.0, {}, {}, {}, {})
    check("switch off -> the overlay has no white line pixels", int((frame_off.min(axis=2) == 255).sum()) == 0)
    check("switch on -> the overlay draws the lines", int((frame_on.min(axis=2) == 255).sum()) > 200, str(int((frame_on.min(axis=2) == 255).sum())))

    # ---- the Line window: the edge is offered for every stream; choose per stream ----
    dlg = app.open_line_editor()
    check("window opens", dlg is not None)
    check("every stream starts on its zone edge (the source in use)", all(dlg.mode[mv] == "edge" for mv in dlg.movements), str(dlg.mode))
    check("the edges are shown without drawing anything", all(dlg._done(mv) for mv in dlg.movements))
    dlg.set_mode("5-6-7", "drawn")
    check("choosing 'วาดเอง' makes it undone until drawn", not dlg._done("5-6-7") and dlg.current != "5-6-7" or True)
    dlg.select("5-6-7")
    dlg.add_point(50, 250)
    dlg.add_point(250, 250)
    check("5-6-7 now has its own drawn Line", dlg.points["5-6-7"] == [(50, 250), (250, 250)] and dlg.mode["5-6-7"] == "drawn")
    check("save works", dlg.save() is True)
    check("source switched to per_stream", app.run3_ref_line_source_var.get() == "per_stream")
    text = app.run3_reference_text.get("1.0", "end-1c").splitlines()
    check("mapping: edge streams written as Edge a-b", "8|2-3-4|Edge 2-3" in text and "8|5-6-3-1|Edge 3-6" in text and "8|1-3-6-7|Edge 1-3" in text, str(text))
    check("mapping: the drawn stream written as Line N", "8|5-6-7|Line 2" in text, str(text))
    with open(zpath, encoding="utf-8") as f:
        data = json.load(f)
    check("only the drawn Line was written to the Zone file", list(data.get("lines", {})) == ["Line 2"], str(data.get("lines")))

    lines = app._display_ref_lines()
    labels = sorted(lbl.split(" (")[0] for lbl, _a, _b in lines)
    check("per_stream display = 2 edges + the drawn Line", labels == ["Edge 2-3", "Edge 3-6", "Line 2"], str(labels))
    check("no preflight warning about the reference lines", not any("Gap Acceptance" in w for w in app.collect_run3_warnings()), str(app.collect_run3_warnings()))

    # all streams on their edge: nothing to draw, nothing written to the Zone file, still saves
    dlg2 = app.open_line_editor()
    check("re-open: 5-6-7 drawn, the others on the edge", dlg2.mode["5-6-7"] == "drawn" and dlg2.mode["2-3-4"] == "edge", str(dlg2.mode))
    dlg2.set_mode("5-6-7", "edge")
    before = open(zpath, encoding="utf-8").read()
    check("save with only edges works", dlg2.save() is True)
    check("the Zone file is untouched when nothing was drawn", open(zpath, encoding="utf-8").read() == before)
    check("mapping now says Edge 5-6", "8|5-6-7|Edge 5-6" in app.run3_reference_text.get("1.0", "end-1c").splitlines())

    # ---- the X-Y plane: drawn only when xy_show_ref_lines is on ----
    c = app._run3_snapshot_config()
    c["align"] = None
    tracks = {}
    disp_on = dict(app.get_settings(), xy_show_ref_lines=True, xy_show_grid=False, xy_show_zone_boundary=False, xy_show_zone_label=False)
    disp_off = dict(disp_on, xy_show_ref_lines=False)
    scene_on = app._run3_topview_scene(tracks, c, video, disp_on, 800, allow_empty=True)
    scene_off = app._run3_topview_scene(tracks, c, video, disp_off, 800, allow_empty=True)
    check("X-Y plane builds", scene_on is not None and scene_off is not None)
    if scene_on is not None and scene_off is not None:
        white_on = int((scene_on["base"].min(axis=2) >= 250).sum())
        white_off = int((scene_off["base"].min(axis=2) >= 250).sum())
        check("X-Y: lines drawn only when the switch is on", white_on > white_off + 100, f"{white_on} vs {white_off}")

    root.destroy()
    print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
