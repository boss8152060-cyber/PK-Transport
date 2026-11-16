"""Settings of PK Transport and the Python command that starts things: no GUI.

modules.json (next to main.py) is the registry of the modules (see pkt/modman.py); pkt_settings.json (the user's own, not in git)
holds the language, the choices of the pages, and per module a linked development folder and a Python command.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODULES_FILE = os.path.join(ROOT, "modules.json")
SETTINGS_FILE = os.path.join(ROOT, "pkt_settings.json")


def load_settings(path=SETTINGS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings, path=SETTINGS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def python_command(override=""):
    """The command (list) that starts a module: the user's override, else this Python when it is a virtual environment, else `py -3.12` on Windows when that works, else this Python."""
    override = (override or "").strip()
    if override:
        import shlex
        parts = shlex.split(override, posix=(os.name != "nt"))
        return [q[1:-1] if len(q) >= 2 and q[0] == q[-1] and q[0] in "\"'" else q for q in parts]      # (Windows split keeps the quotes)
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return [sys.executable]                  # running inside the private environment of install.bat (.venv): the modules use it too
    if os.name == "nt":
        try:
            r = subprocess.run(["py", "-3.12", "-V"], capture_output=True, timeout=8)
            if r.returncode == 0:
                return ["py", "-3.12"]
        except (OSError, subprocess.SubprocessError):
            pass
    return [sys.executable]
