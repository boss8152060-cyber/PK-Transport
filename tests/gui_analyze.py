"""Headless test of PKT Analyze embedded in the window (needs PKT-Analyze next to this app and torch / ultralytics installed).

Run from the PK-Transport folder:   py -3.12 tests/gui_analyze.py
"""
import json
import os
import sys
import tempfile
import time
import tkinter as tk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pkt.ui import app as A  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


if not os.path.isfile(os.path.join(ROOT, "PKT-Analyze", "Run", "PKStudio.py")):
    print("SKIP: PKT-Analyze is not next to this app")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="pkt_ga_")
settings_path = os.path.join(tmp, "pkt_settings.json")
model = os.path.join(tmp, "mine.pt")
with open(model, "wb") as f:
    f.write(b"x")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump({"auto_check_updates": False, "language": "en", "shared": {"analyze_model": model}}, f)
root = tk.Tk()
app = A.PKTApp(root, settings_path=settings_path)
page = app.pages["analyze"]
root.update()
check("nothing of PKT Analyze is loaded before the page is opened", page.loaded is False and page.studio is None)
check("Open on the PKT Analyze card opens the page, not a program", app.launch("analyze") is page and app.current == "analyze")
root.update()
check("a loading message shows while PyTorch loads", page.loading and "Loading" in str(page.message.cget("text")))
end = time.time() + 180
while time.time() < end and not page.loaded:
    root.update()
    time.sleep(0.05)
check("the module loads", page.loaded and page.error is None, str(page.error))
root.update()
check("its window is built into the page", page.studio is not None and page.studio.root is page.shell and page.shell.winfo_ismapped())
check("it has its five steps", page.studio is not None and len(page.studio.notebook.tabs()) == 5)
check("the model chosen in PK Transport is not forced when the file is not the module's own (it exists, so it is used)", page.studio.model_var.get() in (model, page.applied_model))
check("closing the program while nothing runs does not ask", page.is_running() is False)
check("the other pages still work", all(app.show(n) is app.pages[n] for n in ("train", "data", "settings", "home")))
app.show("analyze")
root.update()
check("coming back shows it again", page.shell.winfo_ismapped())
asked = []
A.messagebox.askyesno = lambda t, m, **k: (asked.append(m), True)[1]
page.studio.running = True
app.on_close()
check("closing while it processes asks, then asks the run to stop", len(asked) == 1 and page.studio.stop_event.is_set())
page.studio.running = False
root.update()
time.sleep(1)
try:
    root.update()
except tk.TclError:
    pass
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
