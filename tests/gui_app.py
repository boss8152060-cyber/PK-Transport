"""Headless test of the PK Transport window (hidden Tk): shell, navigation, language switch, home cards, launching fake modules, settings.

Run from the PK-Transport folder:   py -3.12 tests/gui_app.py
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

from pkt import shared  # noqa: E402
from pkt.ui import app as A  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


tmp = tempfile.mkdtemp(prefix="pkt_gui_")
A.LOG_DIR = os.path.join(tmp, "logs")
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
        {"id": "train", "name": "PKT Train", "path": "ModTrain", "entry": None, "page": "train", "version_file": None},
        {"id": "analyze", "name": "PKT Analyze", "path": "ModAnalyze", "entry": "go.py", "version_file": None},
    ]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False}, f)

shown = []
A.messagebox.showerror = lambda title, msg, **k: shown.append(msg)

root = tk.Tk()
app = A.PKTApp(root, settings_path=settings_path, defs_path=defs_path, project_root=tmp)
root.update()
home = app.pages["home"]
text = lambda w: str(w.cget("text"))  # noqa: E731

check("one page per area", list(app.pages) == ["home", "data", "train", "analyze", "settings"], str(list(app.pages)))
check("one card per module on Home", list(home.cards) == ["data", "train", "analyze"])
check("the window starts on Home", app.current == "home")
check("default language is Thai", app.tr.lang == "th" and "พบ" in text(home.cards["data"]["chip"]), text(home.cards["data"]["chip"]))
check("Open is enabled for a module with a start file or a page",
      all(str(home.cards[m]["open"].cget("state")) == "normal" for m in ("data", "analyze")) is True)
check("the module folder comes from the defaults", app.info_of("data")[1]["folder"] == os.path.join(tmp, "ModData"))

# navigation
for name in ("data", "train", "analyze", "settings", "home"):
    check(f"navigation shows the {name} page", app.show(name) is app.pages[name] and app.current == name)
check("an unknown page is ignored", app.show("nope") is None and app.current == "home")

# language switch (live, every page)
app.set_language("en")
root.update()
check("switching to English changes the chip", text(home.cards["data"]["chip"]) == "✓ Found", text(home.cards["data"]["chip"]))
check("the language is saved", json.load(open(settings_path, encoding="utf-8"))["language"] == "en")
root2 = tk.Tk()
root2.withdraw()
app2 = A.PKTApp(root2, settings_path=settings_path, defs_path=defs_path, project_root=tmp)
check("a new window starts in the saved language", app2.tr.lang == "en")
root2.destroy()
app.set_language("th")
root.update()
check("switching back to Thai works", "พบ" in text(home.cards["data"]["chip"]))
app.set_language("en")

# launching
proc = app.launch("data")                     # the fake PKT Data here has no "page", so it starts as a program (the real one opens its tab)
check("launching a module starts its process and says so", proc is not None and proc.poll() is None and "PKT Data" in app.status_var.get())
check("its output goes to a log file", os.path.isfile(os.path.join(A.LOG_DIR, "data.log")))
proc.kill()
proc.wait()

proc = app.launch("analyze")
for _ in range(50):
    if proc.poll() is not None:
        break
    time.sleep(0.1)
shown.clear()
app._check_early_exit("analyze", "PKT Analyze", proc, os.path.join(A.LOG_DIR, "analyze.log"))
check("a module that closes at once with an error is reported with its log", len(shown) == 1 and "3" in shown[0] and "analyze.log" in shown[0], str(shown))
check("its error output is in the log", b"boom" in open(os.path.join(A.LOG_DIR, "analyze.log"), "rb").read())

shown.clear()
check("PKT Train opens as a page of this window", app.launch("train") is app.pages["train"] and app.current == "train" and not shown)
app.show("home")

settings_missing = {"modules": {"data": {"path": os.path.join(tmp, "NoSuchFolder")}}}
app.settings = settings_missing
app.refresh_modules()
check("a missing folder is shown as missing and Open is disabled", text(home.cards["data"]["chip"]).startswith("⚠") and str(home.cards["data"]["open"].cget("state")) == "disabled")
check("launching a missing module shows the error", app.launch("data") is None and len(shown) == 1 and "NoSuchFolder" in shown[0])
app.settings = {"language": "en", "auto_check_updates": False}
app.refresh_modules()

# the model for PKT Analyze
model_file = os.path.join(tmp, "mymodel.pt")
with open(model_file, "wb") as f:
    f.write(b"x")
with open(os.path.join(tmp, "ModAnalyze", "go.py"), "w") as f:
    f.write("import os\nopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env.txt'), 'w').write(os.environ.get('PKT_MODEL_PATH', 'NONE'))\nimport time; time.sleep(30)")
check("the model starts empty", shared.get_analyze_model(app.settings) == "")
check("saving the model works", app.set_analyze_model(model_file) is True)
check("the model is saved in the settings", json.load(open(settings_path, encoding="utf-8"))["shared"]["analyze_model"] == os.path.normpath(model_file))
check("Home shows the model", "mymodel.pt" in text(home.cards["analyze"]["metric"]), text(home.cards["analyze"]["metric"]))
proc = app.launch("analyze")
env_file = os.path.join(tmp, "ModAnalyze", "env.txt")
for _ in range(60):
    if os.path.isfile(env_file) and open(env_file).read():
        break
    time.sleep(0.1)
check("PKT Analyze is started with PKT_MODEL_PATH", open(env_file).read() == os.path.normpath(model_file))
proc.kill()
proc.wait()
app.set_analyze_model("")
check("clearing the model forgets it", shared.get_analyze_model(app.settings) == "")

# open folder
opened = []
app._open_path = lambda p: opened.append(p)
check("Open folder opens the module folder", app.open_folder("data") is True and opened == [os.path.join(tmp, "ModData")])
shown.clear()
app.settings = settings_missing
check("Open folder of a missing module shows an error", app.open_folder("data") is False and len(shown) == 1)
app.settings = {"language": "en", "auto_check_updates": False}
app.refresh_modules()

# settings page
sp = app.pages["settings"]
other = os.path.join(tmp, "ModData2")
os.makedirs(other)
sp.folder_vars["data"].set(other)
sp.python_vars["data"].set("py -3.12")
sp.save()
saved = json.load(open(settings_path, encoding="utf-8"))
check("only what differs from modules.json is saved", saved["modules"] == {"data": {"path": os.path.normpath(other), "python": "py -3.12"}}, str(saved.get("modules")))
check("the module follows the new folder", app.info_of("data")[1]["folder"] == os.path.normpath(other))
sp.auto_var.set(True)
sp.save()
check("the check-at-start choice is saved", json.load(open(settings_path, encoding="utf-8"))["auto_check_updates"] is True)

# layout: cards and buttons inside the window
root.deiconify()
app.show("home")
root.update()
w = root.winfo_width()
inside = all(c["open"].winfo_rootx() + c["open"].winfo_width() <= root.winfo_rootx() + w for c in home.cards.values())
check("the cards and their buttons fit the window", inside, f"window {w}px")

# closing: nothing running -> closes without asking
asked = []
A.messagebox.askyesno = lambda t, m, **k: (asked.append(m), True)[1]
app.on_close()
check("closing with no training running does not ask", not asked)

print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
