"""Headless test of the module manager in the window (hidden Tk) against a fake GitHub: install / update / switch version / uninstall,
the pages of the modules, Home, the restart notice, closing while a module works.

Run from the PK-Transport folder:   py -3.12 tests/gui_modules.py
No network, no pip: the libraries step is replaced by a recorder; the modules are tiny fake ones with a real plugin file."""
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

from pkt import envsetup, modman  # noqa: E402
from pkt.ui import app as A  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


# ---------------------------------------------------------------- a fake GitHub with three fake modules
PLUGIN = '''
import tkinter as tk
from tkinter import ttk
API = 1
VERSION = "{version}"
STATE = {{"running": False, "stopped": False}}

def texts():
    return {{"th": {{"fake_{mid}": "ข้อความของ {mid}"}}, "en": {{"fake_{mid}": "text of {mid}"}}}}

def summary(app, folder):
    return "summary {mid} {version}"

def recent(app, folder):
    return [{{"mtime": 1700000000.0, "glyph": "*", "title": "recent of {mid} {version}", "meta": "meta"}}]

class Page(ttk.Frame):
    def __init__(self, parent, app, folder):
        super().__init__(parent)
        self.label = ttk.Label(self, text="PAGE {mid} {version}")
        self.label.pack()
    def is_running(self):
        return STATE["running"]
    def stop_for_exit(self):
        STATE["stopped"] = True

def create(parent, app, folder):
    return Page(parent, app, folder)
'''


def module_zip(mid, version, min_shell="2.0.0"):
    top = f"PKT-{mid}-x"
    manifest = {"api": 1, "id": mid, "name": f"PKT {mid.title()}", "version": version, "min_shell": min_shell, "plugin": "pkt_plugin.py",
                "requirements": ["pyyaml"], "needs_torch": mid != "data"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{top}/pkt_module.json", json.dumps(manifest))
        z.writestr(f"{top}/pkt_plugin.py", PLUGIN.format(mid=mid, version=version))
    return buf.getvalue()


class Fake(http.server.BaseHTTPRequestHandler):
    tags = {}     # repo -> [tag names]
    zips = {}     # (repo, tag) -> bytes

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        parts = path.strip("/").split("/")
        code, body = 404, b"{}"
        if parts[:1] == ["repos"] and parts[-1] == "tags":
            repo = "/".join(parts[1:3])
            page = int(self.path.rpartition("page=")[2] or 1)
            code, body = 200, json.dumps([{"name": n} for n in (Fake.tags.get(repo, []) if page == 1 else [])]).encode()
        elif "archive" in parts:
            repo = "/".join(parts[:2])
            tag = parts[-1][:-4]
            data = Fake.zips.get((repo, tag))
            if data is not None:
                code, body = 200, data
        elif parts == ["pkt", "__init__.py"]:
            code, body = 200, b'__version__ = "2.0.0"\n'
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def publish(mid, version, **kw):
    repo = f"o/PKT-{mid.title()}"
    tag = f"v{version}"
    Fake.tags.setdefault(repo, [])
    if tag not in Fake.tags[repo]:
        Fake.tags[repo].append(tag)
    Fake.zips[(repo, tag)] = module_zip(mid, version, **kw)


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"

tmp = tempfile.mkdtemp(prefix="pkt_gm_")
defs_path = os.path.join(tmp, "modules.json")
with open(defs_path, "w", encoding="utf-8") as f:
    json.dump({"modules": [{"id": m, "name": f"PKT {m.title()}", "repo": f"o/PKT-{m.title()}", "tag_regex": r"^v(\d+\.\d+\.\d+)$", "desc_key": f"{m}_desc"}
                           for m in ("data", "train", "analyze")]}, f)
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"language": "en", "auto_check_updates": False}, f)
for m in ("data", "train", "analyze"):
    publish(m, "1.0.0")
publish("data", "1.1.0")

prepared = []
envsetup.prepare_module = lambda manifest, folder, log=print, **k: (prepared.append(manifest["id"]), log("libraries ok"))
shown, asked = [], []
answer = [True]
A.messagebox.showerror = lambda t, m, **k: shown.append(m)
A.messagebox.showinfo = lambda t, m, **k: shown.append(m)
A.messagebox.askyesno = lambda t, m, **k: (asked.append(m), answer[0])[1]

root = tk.Tk()
root.geometry("1220x780+10+10")
github = {"api_base": base, "zip_url": base + "/{repo}/archive/refs/tags/{tag}.zip", "raw_url": base + "/", "app_zip_url": base + "/o/PK-Transport/archive/main.zip"}
app = A.PKTApp(root, settings_path=settings_path, defs_path=defs_path, project_root=tmp, github=github)


def pump(cond=None, seconds=20):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if cond and cond():
            return True
        time.sleep(0.03)
    return cond is None


home, mods = app.pages["home"], app.pages["modules"]
SHOTS = os.environ.get("PKT_SHOT_DIR")                  # set it to keep screenshots of the main states (for the documentation)


def shot(name):
    if not SHOTS:
        return
    from PIL import ImageGrab
    root.attributes("-topmost", True)
    pump(seconds=0.8)
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    os.makedirs(SHOTS, exist_ok=True)
    ImageGrab.grab((x, y, x + w, y + h)).save(os.path.join(SHOTS, name + ".png"))


# ---------------------------------------------------------------- nothing installed
pump(seconds=0.5)
check("the window has Home, the three modules, Modules and Settings", list(app.pages) == ["home", "data", "train", "analyze", "modules", "settings"])
check("nothing is installed at the start", not any(app.state_of(m)["installed"] for m in app.module_ids))
check("Home tells what to do when nothing is installed", home._empty_shown)
check("a module page without the module shows the note and an Install button", app.show("data") is app.pages["data"] and app.pages["data"].page is None
      and "not installed" in str(app.pages["data"].note_text.cget("text")))
app.show("modules")
check("the Modules page reads the versions from GitHub when it is opened", pump(lambda: set(app.tags) == {"data", "train", "analyze"}), str(app.tags.keys()))
check("it offers Latest and every version, newest first", mods.rows["data"]["combo"]["values"][0].startswith("Latest") and list(mods.rows["data"]["combo"]["values"])[1:] == ["1.1.0", "1.0.0"],
      str(list(mods.rows["data"]["combo"]["values"])))
shot("modules_empty")
check("the state chips say Not installed", all("Not installed" in str(r["chip"].cget("text")) for r in mods.rows.values()))

# ---------------------------------------------------------------- install the newest / a chosen version
check("install the newest PKT Data", app.install_module("data") is True)
check("a second operation at the same time is refused", app.install_module("train") is False and shown and "Another module operation" in shown[-1])
check("the install finishes", pump(lambda: not app.mod_busy and app.state_of("data")["installed"]))
st = app.state_of("data")
check("the newest version was installed (1.1.0)", st["version"] == "1.1.0" and st["tag"] == "v1.1.0" and os.path.isfile(os.path.join(tmp, "modules", "data", "pkt_plugin.py")))
check("its libraries were prepared", prepared == ["data"])
check("the log shows the steps", any("Downloading" in line for line in app.mod_log) and any("libraries ok" in line for line in app.mod_log))
mods.refresh()
check("the Modules page shows it as installed", "Installed 1.1.0" in str(mods.rows["data"]["chip"].cget("text")))
combo = mods.rows["train"]["combo"]
combo.current(1)                                                                                          # PKT Train: version 1.0.0 is the only one
check("install a chosen version", mods._selected_tag("train") == "v1.0.0")
mods._main_action("train")
check("it is installed", pump(lambda: not app.mod_busy and app.state_of("train")["installed"]) and app.state_of("train")["version"] == "1.0.0")

# ---------------------------------------------------------------- the module pages and Home
app.show("data")
check("the page of the module is created from its plugin", pump(lambda: app.pages["data"].page is not None) and "PAGE data 1.1.0" in str(app.pages["data"].page.label.cget("text")))
check("the page is among the areas of the language switch", app.pages["data"].page in app.xl.areas)
check("the module's own texts are available", app.t("fake_data") == "text of data")
app.set_language("th")
check("... and follow the language", app.t("fake_data") == "ข้อความของ data")
app.set_language("en")
app.show("home")
pump(seconds=0.3)
check("Home shows the version, the summary and the recent work of the module", "summary data 1.1.0" in str(home.cards["data"]["metric"].cget("text"))
      and "1.1.0" in str(home.cards["data"]["version"].cget("text")))
shot("home_installed")
check("Home no longer asks to install something", not home._empty_shown)
check("a module that is not installed offers Install on its card", str(home.cards["analyze"]["open"].cget("text")) == "Install")
check("an installed module offers Open", str(home.cards["data"]["open"].cget("text")) == "Open")

# ---------------------------------------------------------------- an update appears
publish("data", "1.2.0")
publish("train", "1.1.0")
app.check_updates()
check("the check finds the newer versions", pump(lambda: not app.checking and app.updates.get("data", {}).get("state") == "behind" and app.updates.get("train", {}).get("state") == "behind"))
home.refresh()
check("Home says an update is available", "available" in str(home.update_chip.cget("text")) and str(home.cards["data"]["update_btn"].cget("state")) == "normal")
mods.refresh()
check("the Modules page too", "Update 1.2.0 available" in str(mods.rows["data"]["chip"].cget("text")))

shot("modules_update")
# train was never opened: its plugin is replaced live; data is open: restart is needed
answer[0] = False                                                                                         # "restart now?" -> no
check("update PKT Train (its page was never created)", app.update_module("train") is True and pump(lambda: not app.mod_busy and app.state_of("train")["version"] == "1.1.0"))
check("... no restart needed for it", "train" not in app.restart_needed)
check("the new plugin is the one that loads", app.plugin_of("train").VERSION == "1.1.0")
check("update PKT Data (its page is open)", app.update_module("data") is True and pump(lambda: not app.mod_busy and app.state_of("data")["version"] == "1.2.0"))
check("... then a restart is needed and the user is asked", "data" in app.restart_needed and any("Restart" in m for m in asked))
app.show("data")
pump(seconds=0.3)
check("the old page stays and a notice with the Restart button shows", app.pages["data"].banner.winfo_ismapped() and "PAGE data 1.1.0" in str(app.pages["data"].page.label.cget("text")))

shot("data_restart_banner")
# ---------------------------------------------------------------- go back to an older version, uninstall
combo = mods.rows["train"]["combo"]
vals = list(combo["values"])
combo.current(vals.index("1.0.0"))
check("choose an older version of PKT Train", mods._selected_tag("train") == "v1.0.0")
answer[0] = True
mods._main_action("train")
check("it is switched back", pump(lambda: not app.mod_busy and app.state_of("train")["version"] == "1.0.0"))
asked.clear()
check("uninstall PKT Train (never opened)", app.uninstall_module("train") is True and not app.state_of("train")["installed"] and any("Remove" in m for m in asked))
check("its files are gone, modules/ keeps the others", sorted(os.listdir(os.path.join(tmp, "modules"))) == ["data"])
check("its plugin was forgotten", "train" not in app.plugins and "pkt_plugin_train" not in sys.modules)
check("the user data folder is not part of modules/", os.path.isdir(os.path.join(tmp, "user_data")))
answer[0] = False
asked.clear()
check("declining the confirmation removes nothing", app.uninstall_module("data") is False and app.state_of("data")["installed"])

# ---------------------------------------------------------------- problems
Fake.zips.pop(("o/PKT-Analyze", "v1.0.0"))
shown.clear()
check("a version that cannot be downloaded is reported", app.install_module("analyze", "v1.0.0") is True and pump(lambda: not app.mod_busy) and shown and "Could not change" in shown[-1])
check("... and nothing was installed", not app.state_of("analyze")["installed"])
publish("analyze", "2.0.0", min_shell="9.0.0")
shown.clear()
app.install_module("analyze", "v2.0.0")
pump(lambda: not app.mod_busy)
check("a module that needs a newer PK Transport is refused with the reason", shown and "9.0.0" in shown[-1])
Fake.tags["o/PKT-Analyze"].remove("v2.0.0")
Fake.zips.pop(("o/PKT-Analyze", "v2.0.0"))

# ---------------------------------------------------------------- install all missing / update all
publish("analyze", "1.0.0")
answer[0] = True
check("install all that are missing", app.install_missing() is True and pump(lambda: not app.mod_busy and not app._queue_after and app.state_of("analyze")["installed"] and app.state_of("train")["installed"]))
check("all three are installed", all(app.state_of(m)["installed"] for m in app.module_ids))
publish("analyze", "1.1.0")
publish("train", "1.2.0")
app.check_updates()
pump(lambda: not app.checking and app.updates.get("analyze", {}).get("state") == "behind")
check("update all takes every newer version", app.update_all() is True
      and pump(lambda: not app.mod_busy and not app._queue_after and app.state_of("analyze")["version"] == "1.1.0" and app.state_of("train")["version"] == "1.2.0" and app.state_of("data")["version"] == "1.2.0"))

# ---------------------------------------------------------------- a development folder (linked) is respected
dev = tempfile.mkdtemp(prefix="pkt_dev_")
with open(os.path.join(dev, "pkt_module.json"), "w", encoding="utf-8") as f:
    json.dump({"api": 1, "id": "analyze", "name": "PKT Analyze", "version": "9.9.9", "min_shell": "2.0.0"}, f)
app.settings["modules"] = {"analyze": {"path": dev}}
app.refresh_modules()
shown.clear()
check("a linked folder is used and cannot be installed over or uninstalled",
      app.state_of("analyze")["linked"] and app.state_of("analyze")["version"] == "9.9.9" and app.install_module("analyze") is False and app.uninstall_module("analyze") is False and len(shown) == 2)
app.settings["modules"] = {}
app.refresh_modules()

# ---------------------------------------------------------------- closing while a module works
app.show("data")
mod = app.plugins["data"]
mod.STATE["running"] = True
asked.clear()
answer[0] = False
app.on_close()
check("closing while a module works asks first; 'no' keeps the window", len(asked) == 1 and root.winfo_exists() and not mod.STATE["stopped"])
answer[0] = True
app.on_close()
check("'yes' asks the module to stop", mod.STATE["stopped"])
pump(seconds=1.2)

print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
server.shutdown()
sys.exit(1 if failures else 0)
