"""Headless test of the update check / update buttons and the shortcut button of the PK Transport window, with real temporary git repos.

Run from the PK-Transport folder:   py -3.12 tests/gui_updates.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from pkt import launcher as L  # noqa: E402
from pkt import shortcut as SC  # noqa: E402
from test_updates import World, commit_file, git  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


mod_world = World()            # the module's repo
app_world = World()            # this app's repo
plain = tempfile.mkdtemp(prefix="pkt_plain_")
tmp = tempfile.mkdtemp(prefix="pkt_gu_")
defs_path = os.path.join(tmp, "modules.json")
with open(defs_path, "w", encoding="utf-8") as f:
    json.dump({"modules": [
        {"id": "data", "name": "PKT Data", "path": mod_world.mine, "entry": None, "version_file": None},
        {"id": "train", "name": "PKT Train", "path": plain, "entry": None, "version_file": None},
    ]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False, "language": "en"}, f)

shown, asked = [], []
L.messagebox.showerror = lambda t, m, **k: shown.append(m)
L.messagebox.askyesno = lambda t, m, **k: (asked.append(m), answer[0])[1]
answer = [False]

root = tk.Tk()
root.withdraw()
app = L.Launcher(root, settings_path=settings_path, defs_path=defs_path, project_root=app_world.mine)
root.update()


def pump(cond, seconds=40):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if cond():
            return True
        time.sleep(0.05)
    return False


check("with 'check at start' off nothing is checked by itself", app.updates == {} and not app.checking)
check("update buttons start disabled", str(app.cards["data"]["update_btn"].cget("state")) == "disabled")

# up to date
check("the check starts", app.check_updates() is True)
check("a second check while one runs is ignored", app.check_updates() is False)
check("the checks finish", pump(lambda: not app.checking and "data" in app.updates and "app" in app.updates))
check("an up-to-date module says so", app.cards["data"]["update"].cget("text") == "Up to date", app.cards["data"]["update"].cget("text"))
check("a folder that is not a git repo says it cannot be checked", "Not a git folder" in app.cards["train"]["update"].cget("text"), app.cards["train"]["update"].cget("text"))
check("this app's own state is shown in the header", "Up to date" in app.app_update_var.get() and str(app.app_update_btn.cget("state")) == "disabled", app.app_update_var.get())

# new commits on GitHub for the module
mod_world.push_from_other("new.txt", "new feature")
app.check_updates()
check("new commits are seen after the check", pump(lambda: not app.checking and app.updates["data"]["state"] == "behind"))
check("the card tells how many and the Update button is on", "1 new commit" in app.cards["data"]["update"].cget("text") and str(app.cards["data"]["update_btn"].cget("state")) == "normal", app.cards["data"]["update"].cget("text"))
check("checking did not touch the working copy", not os.path.exists(os.path.join(mod_world.mine, "new.txt")))

# declined, then accepted
answer[0] = False
check("declining the confirmation pulls nothing", app.update_module("data") is False and not os.path.exists(os.path.join(mod_world.mine, "new.txt")))
check("the confirmation lists the incoming commits", asked and "new feature" in asked[-1], str(asked[-1:]))
answer[0] = True
check("accepting starts the update", app.update_module("data") is True)
check("the module is updated and shows up to date", pump(lambda: app.updates["data"]["state"] == "uptodate" and os.path.isfile(os.path.join(mod_world.mine, "new.txt"))))
check("the status says it was updated", "PKT Data updated" in app.status_var.get(), app.status_var.get())
check("Update is off again", pump(lambda: str(app.cards["data"]["update_btn"].cget("state")) == "disabled"))

# an update that git refuses (the user's own edit is in the way) loses nothing
mod_world.push_from_other("new.txt", "changed upstream")
with open(os.path.join(mod_world.mine, "new.txt"), "w") as f:
    f.write("my own edit")
app.check_updates()
pump(lambda: not app.checking and app.updates["data"]["state"] == "behind")
shown.clear()
app.update_module("data")
check("a refused update is reported with git's reason and the edit is kept", pump(lambda: len(shown) == 1) and "local changes" in shown[0] and open(os.path.join(mod_world.mine, "new.txt")).read() == "my own edit", str(shown))

# this app's own update
app_world.push_from_other("app_new.txt", "app change")
app.check_updates()
check("this app's new version is offered", pump(lambda: not app.checking and app.updates["app"]["state"] == "behind" and str(app.app_update_btn.cget("state")) == "normal"), app.app_update_var.get())
app.update_module("app")
check("updating the app asks for a restart", pump(lambda: os.path.isfile(os.path.join(app_world.mine, "app_new.txt")) and "Restart" in app.status_var.get()), app.status_var.get())

# offline: the last known state stays and it says so
git(mod_world.mine, "remote", "set-url", "origin", os.path.join(mod_world.tmp, "gone.git"))
app.check_updates()
check("offline keeps the last state and says GitHub could not be reached", pump(lambda: not app.checking and "Could not reach GitHub" in app.cards["data"]["update"].cget("text")), app.cards["data"]["update"].cget("text"))

# Thai
app.set_language("th")
root.update()
check("the card update line is Thai", "GitHub" in app.cards["data"]["update"].cget("text") and "เชื่อมต่อ" in app.cards["data"]["update"].cget("text"), app.cards["data"]["update"].cget("text"))
app.set_language("en")

# settings: auto check + shortcut
top = app.open_settings()
root.update()
check("the settings dialog has the check-at-start box (off here)", top.auto_var.get() is False)
top.auto_var.set(True)
made = []
orig = SC.create_shortcut
out_dir = tempfile.mkdtemp(prefix="pkt_sc_")
L.shortcut.create_shortcut = lambda root_, **k: (made.append(root_), orig(root_, folder=out_dir, name="PK Transport GUI Test"))[1]
check("the shortcut button makes a shortcut", app.create_shortcut() is True and os.path.isfile(os.path.join(out_dir, "PK Transport GUI Test.lnk")) and "Shortcut created" in app.status_var.get(), app.status_var.get())
L.shortcut.create_shortcut = lambda root_, **k: (False, "boom")
shown.clear()
check("a failed shortcut is reported", app.create_shortcut() is False and len(shown) == 1 and "boom" in shown[0])
app._save_settings(top.settings_vars, top)
check("the check-at-start choice is saved", json.load(open(settings_path, encoding="utf-8"))["auto_check_updates"] is True)

root.destroy()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
