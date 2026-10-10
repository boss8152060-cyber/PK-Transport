"""PKT Train (no GUI): the model families / sizes, reading and patching the training scripts of PKT-Train, running them.

The training scripts (PKT-Train/*.py) are written as Colab cells and also run on this PC. This module never edits them:
it reads their default settings, and makes a PATCHED COPY of the text (model size, epochs, ...) to run here or to copy to Colab.
"""
import os
import re
import subprocess
import sys

# family id -> (script file, folder name of its runs, Ultralytics-style sizes, default size)
FAMILIES = {
    "yolo26": {
        "name": "YOLO26",
        "script": "Train YOLO26L Augmentation.py",
        "runs_folder": "YOLO26",
        "sizes": ["n", "s", "m", "l", "x"],
        "default_size": "l",
    },
    "rtdetr": {
        "name": "RT-DETR",
        "script": "Train RTDETR-L Augmentation.py",
        "runs_folder": "RT-DETR",
        "sizes": ["l", "x"],
        "default_size": "l",
    },
    "rtdetrv2": {
        "name": "RT-DETRv2",
        "script": "Train RT-DETRv2 PyTorch Augmentation.py",
        "runs_folder": "RTDETRv2",
        "sizes": ["s", "m*", "m", "l", "x"],
        "default_size": "m",
    },
}
FAMILY_ORDER = ["yolo26", "rtdetr", "rtdetrv2"]
TRAINING_MODES = ["auto", "new", "continue_from_run"]

# the numeric settings the page edits: key -> the pattern of the line in the scripts (value must be a plain number)
NUMERIC_KEYS = ["epochs", "imgsz", "batch", "workers", "patience"]


def script_path(train_dir, family):
    return os.path.join(train_dir, FAMILIES[family]["script"])


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _line_re(key):
    # at the start of a line:  key = <number>   (anything after it, e.g. a Colab "# @param" comment, is kept)
    return re.compile(rf"^({re.escape(key)}\s*=\s*)(-?\d+(?:\.\d+)?)", re.M)


def read_defaults(text):
    """The default settings written in a script: numbers for NUMERIC_KEYS, plus model_size, training_mode, source_run_name
    (a key that is not found is left out)."""
    out = {}
    for key in NUMERIC_KEYS:
        m = _line_re(key).search(text)
        if m:
            v = m.group(2)
            out[key] = int(v) if re.fullmatch(r"-?\d+", v) else float(v)
    m = re.search(r'^MODEL_SIZE\s*=\s*"([^"]*)"', text, re.M)
    if m:
        out["model_size"] = m.group(1)
    m = re.search(r'^training_mode\s*=\s*"([^"]*)"', text, re.M)
    if m:
        out["training_mode"] = m.group(1)
    m = re.search(r'^source_run_name\s*=\s*"([^"]*)"', text, re.M)
    if m:
        out["source_run_name"] = m.group(1)
    return out


def patch_text(text, settings):
    """A copy of the script text with the given settings written in (model_size, training_mode, source_run_name and the
    NUMERIC_KEYS). Returns (new_text, list of the keys that were not found in the script)."""
    missing = []
    for key in NUMERIC_KEYS:
        if key in settings and settings[key] not in (None, ""):
            pat = _line_re(key)
            if pat.search(text):
                text = pat.sub(lambda m: f"{m.group(1)}{int(settings[key])}", text, count=1)
            else:
                missing.append(key)
    for key, var in (("model_size", "MODEL_SIZE"), ("training_mode", "training_mode"), ("source_run_name", "source_run_name")):
        if settings.get(key) not in (None, ""):
            pat = re.compile(rf'^({var}\s*=\s*)"[^"]*"', re.M)
            if pat.search(text):
                text = pat.sub(lambda m: f'{m.group(1)}"{settings[key]}"', text, count=1)
            else:
                missing.append(key)
    return text, missing


def cell_numbers(text):
    return [int(n) for n in re.findall(r"^# %% \[Cell (\d+)\]", text, re.M)]


def extract_cell(text, number):
    """The text of one Colab cell (from its '# %% [Cell N]' line to the line before the next one), or None."""
    m = re.search(rf"^# %% \[Cell {number}\]", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^# %% \[Cell \d+\]", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[m.start():end].rstrip() + "\n"


def extract_cells_from(text, first=1):
    """All the cells from `first` to the end (what is pasted into Colab, without the header text of the file)."""
    m = re.search(rf"^# %% \[Cell {first}\]", text, re.M)
    return text[m.start():] if m else None


def default_store_dir(train_dir, family):
    return os.path.join(train_dir, "Runs", FAMILIES[family]["runs_folder"])


def build_env(family, size, dataset_dir, store_dir, base_env=None):
    """The environment of a local training process (the scripts read the PKT_* variables)."""
    env = dict(base_env if base_env is not None else os.environ)
    env.update({"PKT_MODEL_SIZE": size, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    if dataset_dir:
        env["PKT_DATASET_DIR"] = dataset_dir
    if store_dir:
        env["PKT_STORE_DIR"] = store_dir
    return env


def stop_flag_path(store_dir):
    return os.path.join(store_dir, "STOP.flag")


def write_run_script(train_dir, family, settings, stamp):
    """Write the patched copy of the family's script into PKT-Train/_workspace/_gui_runs and return (path, missing keys)."""
    text = read_text(script_path(train_dir, family))
    new, missing = patch_text(text, settings)
    out_dir = os.path.join(train_dir, "_workspace", "_gui_runs")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{family}_{stamp}.py")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    return path, missing


def kill_process_tree(proc):
    """Stop a training process and its dataloader workers (the run can be resumed later)."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            proc.terminate()
        except OSError:
            pass


ENV_PROBE = ("import json,sys\n"
             "out={'python':sys.version.split()[0]}\n"
             "try:\n"
             "    import torch\n"
             "    out['torch']=torch.__version__\n"
             "    out['cuda']=bool(torch.cuda.is_available())\n"
             "    if out['cuda']:\n"
             "        p=torch.cuda.get_device_properties(0); out['gpu']=p.name; out['vram_gb']=round(p.total_memory/1024**3,1)\n"
             "except Exception as e:\n"
             "    out['torch_error']=str(e)[:80]\n"
             "try:\n"
             "    import ultralytics\n"
             "    out['ultralytics']=ultralytics.__version__\n"
             "except Exception as e:\n"
             "    out['ultralytics_error']=str(e)[:80]\n"
             "print(json.dumps(out))\n")


def probe_environment(python_cmd, timeout=90):
    """What the training Python has: {'python','torch','cuda','gpu','vram_gb','ultralytics',...} or {'error': text}."""
    import json
    try:
        r = subprocess.run(list(python_cmd) + ["-c", ENV_PROBE], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": str(exc)[:120]}
    for line in reversed(r.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {"error": (r.stderr.strip().splitlines() or ["no output"])[-1][:120]}


def parse_progress(line):
    """(epoch, total or None) from a training log line, or None."""
    m = re.search(r"\[epoch (\d+)/(\d+)\]", line)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"\s+(\d+)/(\d+)\s", line)           # Ultralytics progress row:   "      3/300   ..."
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\(epoch (\d+)\)", line)           # the [backup] line of the scripts
    if m:
        return int(m.group(1)), None
    return None
