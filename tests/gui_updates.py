"""Headless test of the update of PK Transport itself in the window (hidden Tk): a git checkout (real temporary repos) and a "Download ZIP"
folder (fake GitHub on a local web server). The updates of the modules are tested in gui_modules.py.

Run from the PK-Transport folder:   py -3.12 tests/gui_updates.py
"""
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import time
import tkinter as tk
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from pkt import shortcut as SC  # noqa: E402
from pkt.ui import app as A  # noqa: E402
from test_updates import World, git  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


# ---------------------------------------------------------------- a fake GitHub for the zip mode
VERSION = ["2.0.0"]


def app_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("PK-Transport-main/pkt/__init__.py", f'__version__ = "{VERSION[0]}"\n')
        z.writestr("PK-Transport-main/main.py", f"# version {VERSION[0]}\n")
    return buf.getvalue()


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.endswith("pkt/__init__.py"):
            body = f'__version__ = "{VERSION[0]}"\n'.encode()
        elif self.path.endswith(".zip"):
            body = app_zip()
        else:
            body = b"[]"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
github = {"api_base": base, "zip_url": base + "/{repo}/archive/refs/tags/{tag}.zip", "raw_url": base + "/", "app_zip_url": base + "/o/PK-Transport/archive/main.zip"}

app_world = World()            # this app's repo (a git checkout)
tmp = tempfile.mkdtemp(prefix="pkt_gu_")
defs_path = os.path.join(tmp, "modules.json")
with open(defs_path, "w", encoding="utf-8") as f:
    json.dump({"modules": [{"id": m, "name": f"PKT {m.title()}", "repo": f"o/PKT-{m.title()}", "tag_regex": r"^v(\d+\.\d+\.\d+)$", "desc_key": f"{m}_desc"}
                           for m in ("data", "train", "analyze")]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False, "language": "en"}, f)

shown, asked = [], []
answer = [False]
A.messagebox.showerror = lambda t, m, **k: shown.append(m)
A.messagebox.askyesno = lambda t, m, **k: (asked.append(m), answer[0])[1]

root = tk.Tk()
root.withdraw()
app = A.PKTApp(root, settings_path=settings_path, defs_path=defs_path, project_root=app_world.mine, github=github)
root.update()
sp = app.pages["settings"]


def pump(cond, seconds=40):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if cond():
            return True
        time.sleep(0.05)
    return False


# ---------------------------------------------------------------- a git checkout
check("with 'check at start' off nothing is checked by itself", app.updates == {} and not app.checking)
check("the update button starts disabled", str(sp.app_update_btn.cget("state")) == "disabled")
check("the check starts", app.check_updates() is True)
check("a second check while one runs is ignored", app.check_updates() is False)
check("the check finishes", pump(lambda: not app.checking and "app" in app.updates))
check("up to date is shown in the header", "Up to date" in app.app_update_var.get(), app.app_update_var.get())

app_world.push_from_other("app_new.txt", "app change")
app.check_updates()
check("new commits are seen", pump(lambda: not app.checking and app.updates["app"]["state"] == "behind" and str(sp.app_update_btn.cget("state")) == "normal"), app.app_update_var.get())
check("checking did not touch the working copy", not os.path.exists(os.path.join(app_world.mine, "app_new.txt")))
answer[0] = False
check("declining the confirmation pulls nothing", app.update_module("app") is False and not os.path.exists(os.path.join(app_world.mine, "app_new.txt")))
check("the confirmation lists the incoming commits", asked and "app change" in asked[-1], str(asked[-1:]))
answer[0] = True
check("accepting starts the update", app.update_module("app") is True)
check("the app is updated and asks for a restart", pump(lambda: os.path.isfile(os.path.join(app_world.mine, "app_new.txt")) and "Restart" in app.status_var.get()), app.status_var.get())

# an update that git refuses (the user's own edit is in the way) loses nothing
app_world.push_from_other("app_new.txt", "changed upstream")
with open(os.path.join(app_world.mine, "app_new.txt"), "w") as f:
    f.write("my own edit")
app.check_updates()
pump(lambda: not app.checking and app.updates["app"]["state"] == "behind")
shown.clear()
app.update_module("app")
check("a refused update is reported with git's reason and the edit is kept", pump(lambda: len(shown) == 1) and "local changes" in shown[0] and open(os.path.join(app_world.mine, "app_new.txt")).read() == "my own edit", str(shown))

# offline: the last known state stays and it says so
git(app_world.mine, "remote", "set-url", "origin", os.path.join(app_world.tmp, "gone.git"))
app.check_updates()
check("offline keeps the last state and says GitHub could not be reached", pump(lambda: not app.checking and "Could not reach GitHub" in app.app_update_var.get()), app.app_update_var.get())
app.set_language("th")
root.update()
check("the header line is Thai", "เชื่อมต่อ" in app.app_update_var.get(), app.app_update_var.get())
app.set_language("en")

# ---------------------------------------------------------------- a "Download ZIP" folder: version number + zip
zip_root = tempfile.mkdtemp(prefix="pkt_zipapp_")
os.makedirs(os.path.join(zip_root, "pkt"))
with open(os.path.join(zip_root, "pkt", "__init__.py"), "w") as f:
    f.write('__version__ = "1.9.0"\n')
with open(os.path.join(zip_root, "pkt_settings.json"), "w") as f:
    f.write("{}")
root2 = tk.Tk()
root2.withdraw()
app2 = A.PKTApp(root2, settings_path=os.path.join(zip_root, "pkt_settings.json"), defs_path=defs_path, project_root=zip_root, github=github)
root2.update()
app2.check_updates()
end = time.time() + 30
while time.time() < end and (app2.checking or "app" not in app2.updates):
    root2.update()
    time.sleep(0.05)
check("a ZIP folder compares the version number", app2.updates["app"].get("zip") and app2.updates["app"]["state"] == "behind" and "2.0.0" in app2.app_update_var.get(), app2.app_update_var.get())
A.messagebox.askyesno = lambda t, m, **k: (asked.append(m), True)[1]
check("the confirmation names both versions", app2.update_module("app") is True and "1.9.0" in asked[-1] and "2.0.0" in asked[-1])
end = time.time() + 30
while time.time() < end and "Restart" not in app2.status_var.get():
    root2.update()
    time.sleep(0.05)
check("the new files are copied over; the settings stay", open(os.path.join(zip_root, "main.py")).read().strip() == "# version 2.0.0" and open(os.path.join(zip_root, "pkt_settings.json")).read() == "{}")
check("it is up to date afterwards", app2.updates["app"]["state"] == "uptodate")
root2.destroy()

# ---------------------------------------------------------------- settings: auto check + shortcut
check("the settings page has the check-at-start box (off here)", sp.auto_var.get() is False)
sp.auto_var.set(True)
made = []
orig = SC.create_shortcut
out_dir = tempfile.mkdtemp(prefix="pkt_sc_")
A.shortcut.create_shortcut = lambda root_, **k: (made.append(root_), orig(root_, folder=out_dir, name="PK Transport GUI Test"))[1]
check("the shortcut button makes a shortcut", app.create_shortcut() is True and os.path.isfile(os.path.join(out_dir, "PK Transport GUI Test.lnk")) and "Shortcut created" in app.status_var.get(), app.status_var.get())
A.shortcut.create_shortcut = lambda root_, **k: (False, "boom")
shown.clear()
check("a failed shortcut is reported", app.create_shortcut() is False and len(shown) == 1 and "boom" in shown[0])
sp.save()
check("the check-at-start choice is saved", json.load(open(settings_path, encoding="utf-8"))["auto_check_updates"] is True)

root.destroy()
server.shutdown()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
