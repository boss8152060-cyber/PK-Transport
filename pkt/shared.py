"""What the three modules share (no GUI): the trained runs of PKT Train and the model PKT Analyze starts with.

PKT Train writes  <Runs>/<family>/models_<model>/runN/weights/best.pt|best.pth  (+ results.csv, BEST_EPOCH_<epoch>.txt).
PKT Analyze reads the model path from the environment variable PKT_MODEL_PATH (PK Transport sets it when it starts PKT Analyze).
"""
import csv
import os
import re

RUN_RE = re.compile(r"^run(\d+)$")
MODEL_FOLDER_RE = re.compile(r"^models_(.+)$")


def _read_results(path):
    """Rows of an Ultralytics-style results.csv as dicts with stripped keys ([] when missing/unreadable)."""
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]
    except OSError:
        return []


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _best_epoch(weights_dir):
    """The epoch named by the empty marker file BEST_EPOCH_<n>.txt (None when there is none)."""
    try:
        epochs = [int(m.group(1)) for n in os.listdir(weights_dir) if (m := re.match(r"^BEST_EPOCH_(\d+)\.txt$", n))]
    except OSError:
        return None
    return max(epochs) if epochs else None


def describe_run(run_dir, family="", model=""):
    """One trained run: its weights, best epoch and the mAP of that epoch (from results.csv). None when it has no best weights."""
    weights = os.path.join(run_dir, "weights")
    best_pt = os.path.join(weights, "best.pt")
    best_pth = os.path.join(weights, "best.pth")
    if not (os.path.isfile(best_pt) or os.path.isfile(best_pth)):
        return None
    weights_file = best_pt if os.path.isfile(best_pt) else best_pth
    rows = _read_results(os.path.join(run_dir, "results.csv"))
    best_epoch = _best_epoch(weights)
    row = None
    if rows and best_epoch is not None:
        row = next((r for r in rows if _num(r.get("epoch")) == best_epoch), None)
    if row is None and rows:
        row = max(rows, key=lambda r: _num(r.get("metrics/mAP50-95(B)")) or -1.0)
    return {
        "run": os.path.basename(run_dir),
        "family": family,
        "model": model,
        "folder": run_dir,
        "weights": weights_file,
        "usable_in_analyze": weights_file.endswith(".pt"),          # PKT Analyze (Ultralytics) loads .pt; the official RT-DETRv2 .pth is not usable there
        "epochs_done": len(rows),
        "best_epoch": best_epoch if best_epoch is not None else (int(_num(row.get("epoch"))) if row and _num(row.get("epoch")) is not None else None),
        "map50": _num(row.get("metrics/mAP50(B)")) if row else None,
        "map50_95": _num(row.get("metrics/mAP50-95(B)")) if row else None,
        "mtime": os.path.getmtime(weights_file),
    }


def find_runs(root):
    """Every trained run under `root` (a Runs folder, a family folder or a models_<model> folder), newest first."""
    out = []
    if not root or not os.path.isdir(root):
        return out
    root = os.path.normpath(root)
    for dirpath, dirnames, _files in os.walk(root):
        depth = os.path.relpath(dirpath, root).count(os.sep) + (0 if dirpath == root else 1)
        if depth >= 4:
            dirnames[:] = []
        if RUN_RE.match(os.path.basename(dirpath)):
            parent = os.path.basename(os.path.dirname(dirpath))
            m = MODEL_FOLDER_RE.match(parent)
            model = m.group(1) if m else ""
            family = os.path.basename(os.path.dirname(os.path.dirname(dirpath))) if m else ""
            info = describe_run(dirpath, family, model)
            if info:
                out.append(info)
            dirnames[:] = []
    out.sort(key=lambda r: r["mtime"], reverse=True)
    return out


def runs_root_for(store_dir):
    """The folder to scan for a Train page whose runs folder is `store_dir`: the parent when it is a <Runs>/<family> folder
    (so the runs of the other families show too), else the folder itself."""
    if not store_dir:
        return store_dir
    parent = os.path.dirname(os.path.normpath(store_dir))
    return parent if os.path.basename(parent) == "Runs" else store_dir


def analyze_environment(settings, base_env=None):
    """The environment PKT Analyze is started with: the base one + PKT_MODEL_PATH when a model was chosen and still exists."""
    env = dict(base_env if base_env is not None else os.environ)
    model = ((settings or {}).get("shared") or {}).get("analyze_model", "")
    if model and os.path.isfile(model):
        env["PKT_MODEL_PATH"] = model
    else:
        env.pop("PKT_MODEL_PATH", None)         # no stale value from the shell: PKT Analyze then uses its own default
    return env


def set_analyze_model(settings, path):
    """Remember the model for PKT Analyze in the settings dict (empty path = forget it); returns True when it was set."""
    shared = settings.setdefault("shared", {})
    if path and os.path.isfile(path):
        shared["analyze_model"] = os.path.normpath(path)
        return True
    shared.pop("analyze_model", None)
    return False


def get_analyze_model(settings):
    model = ((settings or {}).get("shared") or {}).get("analyze_model", "")
    return model if model and os.path.isfile(model) else ""
