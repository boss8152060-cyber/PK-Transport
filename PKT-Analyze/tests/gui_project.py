"""Save / open a PROJECT: every setting + the Zone / Line geometry + the list of clips with their time ranges and the record choice of each video.

Run from the Run folder:   python tests/gui_project.py"""
import importlib.util
import json
import os
import sys
import tempfile
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pkstudio_main", os.path.join(HERE, "..", "PKStudio.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


tmp = tempfile.mkdtemp(prefix="pk_project_")
real_video = os.path.join(tmp, "a.mp4")
open(real_video, "wb").write(b"x")
path = os.path.join(tmp, "my_project.json")

root = tk.Tk()
root.withdraw()
app = m.Run1App(root)
msgs = []
m.messagebox.showinfo = lambda *a, **k: msgs.append(("info", a))
m.messagebox.showwarning = lambda *a, **k: msgs.append(("warn", a))
m.messagebox.showerror = lambda *a, **k: msgs.append(("error", a))
m.filedialog.asksaveasfilename = lambda **k: path
m.filedialog.askopenfilename = lambda **k: path

app.clips_panel.clear()
app.clips_panel.add_videos([(real_video, "Site/day1"), ("C:/gone/b.mp4", "Site/day1")])
app.clips_panel.clips[0].update({"analysis_start_s": "0:10", "analysis_end_s": "1:00", "save_video": True, "record_start_s": "0:20", "record_end_s": "0:30",
                                 "xy_video": False, "drone_video": True, "drone_start_s": "0:40", "drone_end_s": "0:50"})
app.clips_panel.clips[1].update({"continues_previous": True, "xy_video": True})
app.clips_panel.keep_levels_var.set(2)
app.clips_panel.skip_done_var.set(False)
app.run3_site_id_var.set("77")
app.box_smooth_pct_var.set("65")
app.run3_traj_smooth_method_var.set("mean")
want = [dict(c) for c in app.clips_panel.clips]

app.save_settings()
data = json.load(open(path, encoding="utf-8"))
check("the file has the clips of the list", len(data["project"]["clips"]) == 2 and data["project"]["clips"][0]["drone_start_s"] == "0:40")
check("the file has the settings and the zone geometry too", data["run3"]["site_id"] == "77" and "zone_snapshot" in data and data["box_smooth_pct"] == "65")
check("a save message names the number of clips", msgs and msgs[-1][0] == "info" and "2 คลิป" in msgs[-1][1][1], str(msgs[-1:]))
check("the run settings (get_settings) do NOT carry the list (it would be copied into every clip's settings)", "project" not in app.get_settings())

# a new window opens the project: list, ranges, record choices, ticks and settings come back
app.clips_panel.clear()
app.run3_site_id_var.set("1")
app.box_smooth_pct_var.set("0")
app.clips_panel.keep_levels_var.set(0)
app.clips_panel.skip_done_var.set(True)
msgs.clear()
app.load_settings()
got = [{k: v for k, v in c.items()} for c in app.clips_panel.clips]
check("the list is back with every choice", got == want, str(got)[:300])
check("the ticks of the list are back", app.clips_panel.keep_levels_var.get() == 2 and app.clips_panel.skip_done_var.get() is False)
check("the settings are back", app.run3_site_id_var.get() == "77" and app.box_smooth_pct_var.get() == "65" and app.run3_traj_smooth_method_var.get() == "mean")
check("a video missing on this computer is reported but stays in the list", msgs and msgs[-1][0] == "warn" and "b.mp4" in msgs[-1][1][1] and len(app.clips_panel.clips) == 2, str(msgs[-1:])[:200])

# an old settings file (no project part) leaves the list alone
old = {k: v for k, v in data.items() if k not in ("project", "project_version")}
json.dump(old, open(path, "w", encoding="utf-8"))
msgs.clear()
app.clips_panel.clips = app.clips_panel.clips[:1]
app.load_settings()
check("an older settings file does not touch the list", len(app.clips_panel.clips) == 1 and msgs and msgs[-1][0] == "info" and "ไม่มีรายการคลิป" in msgs[-1][1][1], str(msgs[-1:])[:200])
root.destroy()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
