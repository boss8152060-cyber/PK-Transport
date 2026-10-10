"""Headless test of the PK Transport window (hidden Tk): cards, language switch, launching fake modules, settings.

Run from the PK-Transport folder:   py -3.12 tests/gui_launcher.py
Uses a fake project (temp folder) so it does not depend on the real modules being cloned.
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

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


tmp = tempfile.mkdtemp(prefix="pkt_gui_")
L.LOG_DIR = os.path.join(tmp, "logs")
for folder, entry, body in (("ModData", "go.py", "import time; time.sleep(30)"),
                            ("ModTrain", None, None),
                            ("ModAnalyze", "go.py", "import sys; print('boom'); sys.exit(3)")):
    os.makedirs(os.path.join(tmp, folder))
    if entry:
        with open(os.path.join(tmp, folder, entry), "w") as f:
            f.write(body)
defs_path = os.path.join(tmp, "modules.json")
with open(defs_path, "w", encoding="utf-8") as f:
    json.dump({"modules": [
        {"id": "data", "name": "PKT Data", "path": "ModData", "entry": "go.py", "version_file": None},
        {"id": "train", "name": "PKT Train", "path": "ModTrain", "entry": None, "version_file": None},
        {"id": "analyze", "name": "PKT Analyze", "path": "ModAnalyze", "entry": "go.py", "version_file": None},
    ]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")

shown = []
L.messagebox.showerror = lambda title, msg, **k: shown.append(msg)

root = tk.Tk()
root.withdraw()
app = L.Launcher(root, settings_path=settings_path, defs_path=defs_path, project_root=tmp)
root.update()

check("one card per module", list(app.cards) == ["data", "train", "analyze"])
check("default language is Thai", app.tr.lang == "th" and "ไทย" not in app.cards["data"]["status"].cget("text") and "พบ" in app.cards["data"]["status"].cget("text"))
check("a found module is marked found; the Open button is enabled for modules with a start file",
      str(app.cards["data"]["open"].cget("state")) == "normal" and str(app.cards["analyze"]["open"].cget("state")) == "normal")
check("a module with neither a start file nor a page has Open disabled", str(app.cards["train"]["open"].cget("state")) == "disabled")
check("the card shows the folder", app.cards["data"]["folder"].cget("text") == os.path.join(tmp, "ModData"))
check("technical terms stay in English in the Thai description", all(t in app.cards["analyze"]["version"].master.winfo_children()[0].cget("text") for t in ("TTC", "PET", "LDP")))

# language switch
app.set_language("en")
root.update()
check("switching to English changes the status text", app.cards["data"]["status"].cget("text") == "● Found")
check("the card descriptions are English", "Prepare datasets" in app.cards["data"]["status"].master.winfo_children()[0].cget("text"))
check("the language is saved", json.load(open(settings_path, encoding="utf-8"))["language"] == "en")
app2 = L.Launcher(root, settings_path=settings_path, defs_path=defs_path, project_root=tmp)
check("a new window starts in the saved language", app2.tr.lang == "en")
app2.body.destroy()
app.set_language("th")

# launching
proc = app.launch("data")
check("launching a module starts its process and says so", proc is not None and proc.poll() is None and "PKT Data" in app.status_var.get())
check("its output goes to a log file", os.path.isfile(os.path.join(L.LOG_DIR, "data.log")))
proc.kill()
proc.wait()

proc = app.launch("analyze")
for _ in range(50):
    if proc.poll() is not None:
        break
    time.sleep(0.1)
shown.clear()
app._check_early_exit("analyze", "PKT Analyze", proc, os.path.join(L.LOG_DIR, "analyze.log"))
check("a module that closes at once with an error is reported with its log", len(shown) == 1 and "3" in shown[0] and "analyze.log" in shown[0], str(shown))
check("its error output is in the log", b"boom" in open(os.path.join(L.LOG_DIR, "analyze.log"), "rb").read())

shown.clear()
check("a module without a start file does nothing", app.launch("train") is None and not shown)
settings_missing = {"modules": {"data": {"path": os.path.join(tmp, "NoSuchFolder")}}}
app.settings = settings_missing
app.refresh()
check("a missing folder is shown as not found and the Open button is disabled", "ไม่พบ" in app.cards["data"]["status"].cget("text") and str(app.cards["data"]["open"].cget("state")) == "disabled")
check("launching a missing module shows the error", app.launch("data") is None and len(shown) == 1 and "NoSuchFolder" in shown[0])
app.settings = {}
app.refresh()

# the model for PKT Analyze: the card shows it, the settings dialog edits it, Analyze starts with PKT_MODEL_PATH
from pkt import shared  # noqa: E402

model_file = os.path.join(tmp, "mymodel.pt")
with open(model_file, "wb") as f:
    f.write(b"x")
with open(os.path.join(tmp, "ModAnalyze", "go.py"), "w") as f:
    f.write("import os, sys\nopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env.txt'), 'w').write(os.environ.get('PKT_MODEL_PATH', 'NONE'))\nimport time; time.sleep(30)")
app.settings = {}
check("the settings dialog starts with an empty model", app.open_settings().model_var.get() == "")
top = app.open_settings()
top.model_var.set(model_file)
app._save_settings(top.settings_vars, top)
check("the model chosen in the settings is saved", json.load(open(settings_path, encoding="utf-8"))["shared"]["analyze_model"] == os.path.normpath(model_file))
check("the PKT Analyze card shows the model", "mymodel.pt" in app.cards["analyze"]["note"].cget("text"), app.cards["analyze"]["note"].cget("text"))
proc = app.launch("analyze")
for _ in range(60):
    if os.path.isfile(os.path.join(tmp, "ModAnalyze", "env.txt")) and open(os.path.join(tmp, "ModAnalyze", "env.txt")).read():
        break
    time.sleep(0.1)
check("PKT Analyze is started with PKT_MODEL_PATH", open(os.path.join(tmp, "ModAnalyze", "env.txt")).read() == os.path.normpath(model_file))
proc.kill()
proc.wait()
os.remove(os.path.join(tmp, "ModAnalyze", "env.txt"))
proc = app.launch("data")
check("another module does not get the variable", proc is not None)
proc.kill()
proc.wait()
top = app.open_settings()
top.model_var.set("")
app._save_settings(top.settings_vars, top)
check("clearing the model forgets it and the note goes away", shared.get_analyze_model(app.settings) == "" and app.cards["analyze"]["note"].cget("text") == "")
app.settings = {}
app.refresh()

# open folder
opened = []
app._open_path = lambda p: opened.append(p)
check("Open folder opens the module folder", app.open_folder("data") is True and opened == [os.path.join(tmp, "ModData")])
shown.clear()
app.settings = settings_missing
check("Open folder of a missing module shows an error", app.open_folder("data") is False and len(shown) == 1)
app.settings = {}

# settings dialog
top = app.open_settings()
root.update()
fv, pv = top.settings_vars["data"]
other = os.path.join(tmp, "ModData2")
os.makedirs(other)
fv.set(other)
pv.set("py -3.12")
app._save_settings(top.settings_vars, top)
saved = json.load(open(settings_path, encoding="utf-8"))
check("only what differs from modules.json is saved", saved["modules"] == {"data": {"path": os.path.normpath(other), "python": "py -3.12"}}, str(saved.get("modules")))
check("the card follows the new folder", app.cards["data"]["folder"].cget("text") == os.path.normpath(other))

# layout: every card inside the window, buttons visible
root.deiconify()
root.update()
w = root.winfo_width()
inside = all(c["open"].winfo_rootx() + c["open"].winfo_width() <= root.winfo_rootx() + w for c in app.cards.values())
check("the cards and their buttons fit the window", inside, f"window {w}px")
root.destroy()

print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
