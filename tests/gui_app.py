"""Headless test of the PK Transport shell (hidden Tk): pages, navigation, language switch, the settings page. No module is installed here.

Run from the PK-Transport folder:   py -3.12 tests/gui_app.py
"""
import json
import os
import sys
import tempfile
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from pkt.ui import app as A  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


tmp = tempfile.mkdtemp(prefix="pkt_ga_")
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False}, f)
shown = []
A.messagebox.showerror = lambda t, m, **k: shown.append(m)
A.messagebox.showinfo = lambda t, m, **k: shown.append(m)

root = tk.Tk()
app = A.PKTApp(root, settings_path=settings_path, project_root=tmp, github={"api_base": "http://127.0.0.1:9"})
root.update()
text = lambda w: str(w.cget("text"))  # noqa: E731

check("the registry of the real modules.json has the three modules", app.module_ids == ["data", "train", "analyze"])
check("pages: Home, the modules, Modules, Settings", list(app.pages) == ["home", "data", "train", "analyze", "modules", "settings"])
check("the window starts on Home, in Thai", app.current == "home" and app.tr.lang == "th")
check("nothing is installed and Home says so", not any(app.state_of(m)["installed"] for m in app.module_ids) and app.pages["home"]._empty_shown)
for name in ("data", "train", "analyze", "modules", "settings", "home"):
    check(f"navigation shows the {name} page", app.show(name) is app.pages[name] and app.current == name)
check("an unknown page is ignored", app.show("nope") is None and app.current == "home")
check("the version numbers are offered only from the first module release", all(d.get("min_version") for d in app.defs))

# language
app.show("data")
note_th = text(app.pages["data"].note_text)
app.set_language("en")
root.update()
check("switching to English changes the note of a missing module", text(app.pages["data"].note_text) != note_th and "not installed" in text(app.pages["data"].note_text))
check("the language is saved", json.load(open(settings_path, encoding="utf-8"))["language"] == "en")
root2 = tk.Tk()
root2.withdraw()
app2 = A.PKTApp(root2, settings_path=settings_path, project_root=tmp, github={"api_base": "http://127.0.0.1:9"})
check("a new window starts in the saved language", app2.tr.lang == "en")
root2.destroy()
app.set_language("th")
root.update()
check("switching back works", text(app.pages["data"].note_text) == note_th)

# settings: a linked development folder and a Python command per module
sp = app.pages["settings"]
dev = tempfile.mkdtemp(prefix="pkt_dev_")
default_data = os.path.join(tmp, "modules", "data")
check("the default folder of a module is modules/<id>", app.state_of("data")["folder"] == default_data and sp.folder_vars["data"].get() == default_data)
sp.folder_vars["data"].set(dev)
sp.python_vars["train"].set("py -3.12")
sp.save()
saved = json.load(open(settings_path, encoding="utf-8"))
check("only what differs from the defaults is saved", saved["modules"] == {"data": {"path": os.path.normpath(dev)}, "train": {"python": "py -3.12"}}, str(saved.get("modules")))
check("the linked folder is used", app.state_of("data")["folder"] == os.path.normpath(dev) and app.state_of("data")["linked"])
check("the Python command of a module", app.python_for("train") == ["py", "-3.12"] and app.python_for("data")[0])
sp.folder_vars["data"].set(default_data)
sp.save()
check("going back to the default removes the link", "data" not in (json.load(open(settings_path, encoding="utf-8")).get("modules") or {}) and not app.state_of("data")["linked"])
sp.auto_var.set(True)
sp.save()
check("the check-at-start choice is saved", json.load(open(settings_path, encoding="utf-8"))["auto_check_updates"] is True)

# the model for PKT Analyze (kept by the shell, used by Train / Analyze)
model = os.path.join(tmp, "m.pt")
open(model, "wb").write(b"x")
check("the model for PKT Analyze is remembered", app.set_analyze_model(model) is True and app.get_analyze_model() == os.path.normpath(model))
check("... and forgotten", app.set_analyze_model("") is False and app.get_analyze_model() == "")
check("the user data folder is outside modules/", app.user_data_dir("PKT-Train").startswith(os.path.join(tmp, "user_data")))

app.on_close()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
