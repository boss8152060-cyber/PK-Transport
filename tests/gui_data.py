"""Headless test of PKT Data embedded in the window (needs PKT-Data next to this app and its libraries installed).

Run from the PK-Transport folder:   py -3.12 tests/gui_data.py
"""
import json
import os
import sys
import tempfile
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pkt.ui import app as A  # noqa: E402
from pkt.ui.pages import data as D  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


if not os.path.isdir(os.path.join(ROOT, "PKT-Data", "src", "pk_studio")):
    print("SKIP: PKT-Data is not next to this app")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="pkt_gd_")
settings_path = os.path.join(tmp, "pkt_settings.json")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False, "language": "en"}, f)
root = tk.Tk()
app = A.PKTApp(root, settings_path=settings_path)
page = app.pages["data"]
root.update()
check("nothing of PKT Data is loaded before the page is opened", page.loaded is False and not page.tabs)
check("Open on the PKT Data card opens the tab, not a program", app.launch("data") is page and app.current == "data")
root.update()
check("the six workspaces are created", list(page.tabs) == [k for k, *_ in D.SUBTABS] and page.error is None, str(page.error))
check("the first one is shown", page.current == "data" and page.tabs["data"].winfo_ismapped())
for key, *_ in D.SUBTABS:
    page.show_tab(key)
    root.update()
    check(f"the {key} workspace can be shown", page.tabs[key].winfo_ismapped() and all(not t.winfo_ismapped() for k, t in page.tabs.items() if k != key))
def texts(widget, out=None):
    out = [] if out is None else out
    try:
        out.append(str(widget.cget("text")))
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        texts(child, out)
    return out


page.show_tab("data")
app.set_language("th")
root.update()
check("in Thai the labels of PKT Data are Thai", "1) คิววิดีโอ" in texts(page.tabs["data"]) and "▶  เริ่มดึงเฟรม" in texts(page.tabs["data"]))
check("technical words stay English", any("FPS" in t for t in texts(page.tabs["data"])))
app.set_language("en")
root.update()
check("switching to English restores the original texts", "1) Video Queue" in texts(page.tabs["data"]) and "1) คิววิดีโอ" not in texts(page.tabs["data"]))
app.set_language("th")
page.show_tab("autolabeler")
root.update()
check("a tab opened later is translated at once", any("บันทึก" in t for t in texts(page.tabs["autolabeler"])))
page.show_tab("data")
app.show("home")
root.update()
check("another page hides PKT Data (so its key shortcuts stay quiet)", not page.tabs["zone_editor"].winfo_ismapped())
app.set_language("th")
app.show("data")
root.update()
check("coming back shows the last workspace", page.current == "data" and page.tabs["data"].winfo_ismapped())
check("PKT Train still works after PKT Data changed the styles", app.show("train") is app.pages["train"])
root.update()
root.destroy()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
