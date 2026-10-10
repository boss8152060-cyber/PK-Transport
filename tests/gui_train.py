"""Headless test of the PKT Train page (hidden Tk) with a FAKE PKT-Train folder: model/size choice, settings patched into the
script, a local run with live log / progress / stop flag / kill, the Colab copy button, language switch.

Run from the PK-Transport folder:   py -3.12 tests/gui_train.py
"""
import json
import os
import sys
import tempfile
import time
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from pkt import launcher as L  # noqa: E402
from pkt import train_core as TC  # noqa: E402
from pkt import train_page as TP  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


FAKE = '''"""fake training script"""
# %% [Cell 1] setup
import os, sys, time
# %% [Cell 2] model
MODEL_SIZE = "l"  # @param ["n", "s", "m", "l", "x"]
# %% [Cell 6] train
training_mode = "auto"  # @param ["auto", "new"]
source_run_name = "run9"  # @param {type:"string"}
epochs = 300       # @param {type:"integer"}
imgsz = 640        # @param {type:"integer"}
batch = 48         # @param {type:"integer"}
workers = 24       # @param {type:"integer"}
patience = 15      # @param {type:"integer"}
store = os.environ.get("PKT_STORE_DIR", "")
print("MODEL", os.environ.get("PKT_MODEL_SIZE"), MODEL_SIZE, "EPOCHS", epochs, "MODE", training_mode, flush=True)
print("STORE", store, flush=True)
for ep in range(1, epochs + 1):
    print(f"        {ep}/{epochs}     2.4G     1.23", flush=True)
    time.sleep(0.15)
    if os.path.exists(os.path.join(store, "STOP.flag")):
        print("  [STOP] found", flush=True)
        break
'''

tmp = tempfile.mkdtemp(prefix="pkt_gt_")
train_dir = os.path.join(tmp, "PKT-Train")
os.makedirs(train_dir)
for fam in TC.FAMILIES.values():
    with open(os.path.join(train_dir, fam["script"]), "w", encoding="utf-8") as f:
        f.write(FAKE)
defs_path = os.path.join(tmp, "modules.json")
with open(defs_path, "w", encoding="utf-8") as f:
    json.dump({"modules": [{"id": "train", "name": "PKT Train", "path": "PKT-Train", "entry": None, "page": "train", "version_file": None}]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"modules": {"train": {"python": f'"{sys.executable}"'}}}, f)

shown = []
TP.messagebox.showerror = lambda t, m, **k: shown.append(m)
TP.messagebox.showinfo = lambda t, m, **k: shown.append(m)
TP.messagebox.askyesno = lambda *a, **k: True
L.messagebox.showerror = lambda t, m, **k: shown.append(m)
probes = []
TC.probe_environment = lambda cmd, timeout=90: (probes.append(cmd), {"python": "3.12.7", "torch": "2.6.0", "cuda": True, "gpu": "Fake GPU", "vram_gb": 8.0, "ultralytics": "8.4"})[1]

root = tk.Tk()
root.withdraw()
app = L.Launcher(root, settings_path=settings_path, defs_path=defs_path, project_root=tmp)
root.update()
check("the PKT Train card can be opened (it opens a page, not a program)", str(app.cards["train"]["open"].cget("state")) == "normal")
page = app.launch("train")
root.update()
check("Open on the PKT Train card opens the page", isinstance(page, TP.TrainPage) and app.train_page is page)
check("opening it again brings the same window", app.launch("train") is page)


def pump(cond, seconds=15):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if cond():
            return True
        time.sleep(0.05)
    return False


check("the training Python is checked and shown", pump(lambda: "Fake GPU" in page.env_var.get()), page.env_var.get())
check("the settings Python override is used for the check", probes and probes[0] == [sys.executable], str(probes))

# model / size / defaults
check("YOLO26 is the first family with sizes n s m l x", page.family_var.get() == "yolo26" and list(page.widgets["size"].cget("values")) == ["n", "s", "m", "l", "x"] and page.size_var.get() == "l")
check("the defaults of the script are shown", page.num_vars["epochs"].get() == "300" and page.num_vars["batch"].get() == "48" and page.mode_var.get() == "auto")
page.family_var.set("rtdetr")
page.on_family_changed()
check("RT-DETR has sizes l and x", list(page.widgets["size"].cget("values")) == ["l", "x"] and page.size_var.get() == "l")
page.family_var.set("rtdetrv2")
page.on_family_changed()
check("RT-DETRv2 has sizes s m* m l x and starts on m", list(page.widgets["size"].cget("values")) == ["s", "m*", "m", "l", "x"] and page.size_var.get() == "m")
page.family_var.set("yolo26")
page.on_family_changed()
check("the runs folder follows the family", page.store_var.get() == os.path.join(train_dir, "Runs", "YOLO26"), page.store_var.get())
check("the choice is saved in the settings", json.load(open(settings_path, encoding="utf-8"))["train"]["family"] == "yolo26")

# Colab copy
page.size_var.set("x")
page.num_vars["epochs"].set("12")
page.where_var.set("colab")
page._on_where()
root.update()
check("Colab view hides the local part", not page.local_frame.winfo_ismapped() and page.colab_frame.winfo_ismapped())
check("the copy list has everything / whole file / one entry per cell", len(page.copy_labels) == 2 + 3, str(page.copy_labels))
check("copy everything puts the chosen model and settings in the code", page.copy_colab_code() is True)
clip = root.clipboard_get()
check("the clipboard has the cells from Cell 1 with the new values", clip.startswith("# %% [Cell 1]") and 'MODEL_SIZE = "x"' in clip and "epochs = 12 " in clip and "fake training script" not in clip)
check("the status says what was copied", "Cell 1" in page.status_var.get() or "ทั้งหมด" in page.status_var.get(), page.status_var.get())
page.copy_combo.set(page.copy_labels[page.copy_options.index("cell2")])
page.copy_colab_code()
clip2 = root.clipboard_get()
check("copy one cell puts only that cell", clip2.startswith("# %% [Cell 2]") and "epochs" not in clip2, clip2[:60])
page.copy_combo.set(page.copy_labels[1])
page.copy_colab_code()
check("copy the whole file includes the header text", "fake training script" in root.clipboard_get())

# local run: finishes by the stop flag
page.where_var.set("local")
page._on_where()
store = os.path.join(tmp, "runs_yolo")
page.store_var.set(store)
page.dataset_var.set(os.path.join(tmp, "data"))
page.num_vars["epochs"].set("500")
page.mode_var.set("new")
proc = page.start_training()
check("training starts a process and disables Start", proc is not None and str(page.start_btn.cget("state")) == "disabled" and str(page.stop_btn.cget("state")) == "normal")
check("a second start is refused", page.start_training() is None and any("already" in m or "อยู่แล้ว" in m for m in shown))
check("the log shows the output of the run with the patched settings", pump(lambda: "EPOCHS 500 MODE new" in page.log.get("1.0", "end")), page.log.get("1.0", "end")[:300])
log_text = page.log.get("1.0", "end")
check("the script got the model size and the folders through the environment", "MODEL x x" in log_text and f"STORE {store}" in log_text, log_text[:200])
check("the progress line follows the epoch", pump(lambda: "epoch" in page.progress_var.get() and "/500" in page.progress_var.get()), page.progress_var.get())
check("Stop writes STOP.flag in the runs folder", page.request_stop() is True and os.path.isfile(os.path.join(store, "STOP.flag")))
check("the run ends after the flag and the buttons come back", pump(lambda: str(page.start_btn.cget("state")) == "normal" and "STOP" in page.log.get("1.0", "end")), page.status_var.get())
check("the finished status shows the exit code", "0" in page.status_var.get(), page.status_var.get())

# a stale STOP.flag does not stop the next run at once; kill now ends a run
proc = page.start_training()
check("a STOP.flag left from the earlier run is removed at the start", not os.path.isfile(os.path.join(store, "STOP.flag")))
check("the next run really runs", pump(lambda: "/500" in page.progress_var.get()))
page.kill_now()
check("Stop now ends the process", pump(lambda: proc.poll() is not None and str(page.start_btn.cget("state")) == "normal"))

# language switch updates the open page
title_th = page.top.title()
app.set_language("en")
root.update()
check("the page is translated when the language changes", page.top.title() != title_th and "train a detection model" in page.top.title(), page.top.title())
check("typed values survive the language switch", page.num_vars["epochs"].get() == "500" and page.family_var.get() == "yolo26")
check("technical names stay in English", "YOLO26" in page.family_var.get().upper() or page.family_var.get() == "yolo26")

# missing script
os.remove(os.path.join(train_dir, TC.FAMILIES["yolo26"]["script"]))
shown.clear()
check("a missing script is reported and nothing starts", page.start_training() is None and len(shown) == 1)
check("copying with a missing script is reported", page.copy_colab_code() is False)

# layout: the window shows its main controls
page.top.deiconify()
root.update()
check("the buttons fit inside the window", page.start_btn.winfo_rootx() + page.start_btn.winfo_width() < page.top.winfo_rootx() + page.top.winfo_width())
page.close()
check("closing the page lets the launcher forget it", app.train_page is None)
root.destroy()

print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
