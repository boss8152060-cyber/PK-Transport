"""Headless test of the real PKT Data and PKT Analyze modules inside the window (hidden Tk): their pages, the language switch of their texts.

Run from the PK-Transport folder:
    PKT_MODULES_SRC=<folder with the clones of PKT-Data / PKT-Train / PKT-Analyze>  py -3.12 tests/gui_real_modules.py
PKT Analyze needs torch / ultralytics in this Python; without them its part is skipped.
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

from pkt.ui import app as A  # noqa: E402

SRC = os.environ.get("PKT_MODULES_SRC", "")
if not all(os.path.isfile(os.path.join(SRC, d, "pkt_module.json")) for d in ("PKT-Data", "PKT-Train", "PKT-Analyze")):
    print("SKIP: set PKT_MODULES_SRC to the folder that holds the clones of PKT-Data, PKT-Train and PKT-Analyze")
    sys.exit(0)

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


tmp = tempfile.mkdtemp(prefix="pkt_rm_")
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"language": "th", "auto_check_updates": False,
               "modules": {"data": {"path": os.path.join(SRC, "PKT-Data")}, "train": {"path": os.path.join(SRC, "PKT-Train")},
                           "analyze": {"path": os.path.join(SRC, "PKT-Analyze")}}}, f)
root = tk.Tk()
app = A.PKTApp(root, settings_path=settings_path, project_root=tmp, github={"api_base": "http://127.0.0.1:9"})


def pump(cond=None, seconds=5):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if cond and cond():
            return True
        time.sleep(0.03)
    return cond is None


def texts(widget, out=None):
    out = [] if out is None else out
    try:
        out.append(str(widget.cget("text")))
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        texts(child, out)
    return out


check("the three real modules are usable by this shell", all(app.module_ready(m) for m in app.module_ids), str(app.plugin_errors))
check("Home shows what the plugins summarize", pump(lambda: "mAP" in "".join(texts(app.pages["home"])) or "โมเดลที่เทรน" in "".join(texts(app.pages["home"])), 3))

# ---------------------------------------------------------------- PKT Data
host = app.pages["data"]
app.show("data")
pump(lambda: host.page is not None and host.page.loaded, 10)
page = host.page
check("PKT Data: the six workspaces are created", page is not None and page.error is None and list(page.tabs) == ["data", "autolabeler", "curator_splitter", "analytics", "zone_editor", "other"], str(getattr(page, "error", "")))
check("the first workspace is shown", page.current == "data" and page.tabs["data"].winfo_ismapped())
for key in list(page.tabs):
    page.show_tab(key)
    root.update()
    check(f"the {key} workspace can be shown alone", page.tabs[key].winfo_ismapped() and all(not t.winfo_ismapped() for k, t in page.tabs.items() if k != key))
page.show_tab("data")
app.set_language("th")
pump(seconds=1)
check("in Thai the labels of PKT Data are Thai", "1) คิววิดีโอ" in texts(page.tabs["data"]) and "▶  เริ่มดึงเฟรม" in texts(page.tabs["data"]))
check("technical words stay English", any("FPS" in t for t in texts(page.tabs["data"])))
app.set_language("en")
pump(seconds=1)
check("switching to English restores the original texts", "1) Video Queue" in texts(page.tabs["data"]) and "1) คิววิดีโอ" not in texts(page.tabs["data"]))
app.set_language("th")
page.show_tab("autolabeler")
pump(seconds=1)
check("a workspace opened later is translated at once", any("บันทึก" in t for t in texts(page.tabs["autolabeler"])))
app.show("home")
root.update()
check("another page hides PKT Data (its key shortcuts stay quiet)", not page.tabs["autolabeler"].winfo_ismapped())

# ---------------------------------------------------------------- PKT Analyze
try:
    import torch  # noqa: F401
    import ultralytics  # noqa: F401
    have_torch = True
except ImportError:
    have_torch = False
if have_torch:
    app.set_language("en")
    host = app.pages["analyze"]
    app.show("analyze")
    check("PKT Analyze: a loading message shows while PyTorch loads", host.page is not None and host.page.loading and "Loading" in str(host.page.message.cget("text")))
    pump(lambda: host.page.loaded, 180)
    page = host.page
    check("the module loads", page.loaded and page.error is None, str(page.error))
    pump(seconds=1)
    check("its window is built into the page", page.studio is not None and page.studio.root is page.shell and page.shell.winfo_ismapped())
    check("it has its five steps", len(page.studio.notebook.tabs()) == 5)
    check("in English the Thai texts of PKT Analyze are English", "Open project…" in texts(page.shell) and "เปิดโปรเจกต์…" not in texts(page.shell))
    app.set_language("th")
    pump(seconds=1)
    check("in Thai they are the original Thai", "เปิดโปรเจกต์…" in texts(page.shell))
    check("its default folders are in the user data folder, not in the module", page.studio.output_var.get().startswith(os.path.join(tmp, "user_data", "PKT-Analyze")), page.studio.output_var.get())
    model = os.path.join(tmp, "mine.pt")
    open(model, "wb").write(b"x")
    app.set_analyze_model(model)
    app.show("home")
    app.show("analyze")
    check("a model handed over by PK Transport goes into the Model field", page.studio.model_var.get() == os.path.normpath(model))
    check("closing while nothing runs does not ask", app.pages["analyze"].is_running() is False)
    page.studio.running = True
    check("a running analysis is reported to the window", app.pages["analyze"].is_running() is True)
    page.studio.running = False
else:
    print("SKIP: PKT Analyze needs torch and ultralytics in this Python")

app.on_close()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
