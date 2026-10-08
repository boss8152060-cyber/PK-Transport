"""The list of Run 3 result files to write: ticks per file, saved and loaded with the settings, grey when the indicator is off.

Run from the Run folder:   python tests/gui_csvchoice.py"""
import importlib.util
import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pkstudio_main", os.path.join(HERE, "..", "PKStudio.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(name)


root = tk.Tk()
root.withdraw()
app = m.Run1App(root)
names = [n for n, _k, _t in m.RUN3_CSV_CHOICES]
check("every result file has a tick, all on by default", set(app.run3_csv_vars) == set(names) and all(v.get() for v in app.run3_csv_vars.values()))
check("snapshot: nothing switched off", app._run3_snapshot_config()["csv_off"] == set())
app.run3_csv_vars["Speed.csv"].set(False)
app.run3_csv_vars["Headway.csv"].set(False)
check("snapshot lists the files switched off", app._run3_snapshot_config()["csv_off"] == {"Speed.csv", "Headway.csv"})
st = app.get_settings()
check("settings carry the choice", set(st["run3"]["csv_off"].split(",")) == {"Speed.csv", "Headway.csv"}, st["run3"]["csv_off"])
for v in app.run3_csv_vars.values():
    v.set(True)
app.set_settings(st)
check("the choice is restored from the settings", not app.run3_csv_vars["Speed.csv"].get() and not app.run3_csv_vars["Headway.csv"].get() and app.run3_csv_vars["PET.csv"].get())
app.set_settings(dict(st, run3=dict(st["run3"], csv_off="")))
check("an empty choice in the file turns everything on again", all(v.get() for v in app.run3_csv_vars.values()))
# the tick of an indicator that is switched off is grey
app.run3_pet_enabled_var.set(False)
root.update_idletasks()
cb, key = app._csv_checks["PET.csv"]
check("PET.csv is grey while PET is off", cb.instate(["disabled"]))
app.run3_pet_enabled_var.set(True)
check("... and usable again when PET is on", not cb.instate(["disabled"]))
cb2, _ = app._csv_checks["Indicator_Summary.csv"]
check("the summary file does not depend on one indicator", not cb2.instate(["disabled"]))
root.destroy()
print("FAILED: " + ", ".join(failures) if failures else "ALL OK")
sys.exit(1 if failures else 0)
