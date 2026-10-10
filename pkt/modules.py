"""The three modules of PK Transport: where they are, whether they are there, their version, and how to start them.

No GUI here (the launcher window uses it; the tests exercise it directly).
modules.json (next to main.py) holds the defaults; pkt_settings.json (the user's own, not in git) can override a module's
folder and the Python command.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODULES_FILE = os.path.join(ROOT, "modules.json")
SETTINGS_FILE = os.path.join(ROOT, "pkt_settings.json")


def load_module_defs(path=DEFAULT_MODULES_FILE):
    """The list of module definitions (dicts with id, name, path, entry, version_file, tag_prefix)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return list(data["modules"])


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


def resolve_module(mod_def, settings=None, root=ROOT):
    """Absolute folder / start file of a module and whether they exist.
    A folder set by the user in the settings (modules[id].path) wins over modules.json; a relative folder is relative to `root`."""
    settings = settings or {}
    user = ((settings.get("modules") or {}).get(mod_def["id"]) or {})
    folder = user.get("path") or mod_def["path"]
    if not os.path.isabs(folder):
        folder = os.path.normpath(os.path.join(root, folder))
    entry_name = mod_def.get("entry")
    if not user.get("path") and entry_name and not os.path.isfile(os.path.join(folder, entry_name)):
        for alt in mod_def.get("fallback_paths") or []:              # an older layout of the same module (e.g. PKT-Analyze/Run)
            alt_folder = os.path.normpath(os.path.join(root, alt))
            if os.path.isfile(os.path.join(alt_folder, entry_name)):
                folder = alt_folder
                break
    entry = mod_def.get("entry")
    page = mod_def.get("page")                 # a module opened as a page inside this app (PKT Train) instead of a separate program
    entry_path = os.path.join(folder, entry) if entry else None
    return {
        "id": mod_def["id"],
        "name": mod_def["name"],
        "folder": folder,
        "exists": os.path.isdir(folder),
        "entry": entry,
        "entry_path": entry_path,
        "entry_exists": bool(entry_path and os.path.isfile(entry_path)) or (bool(page) and os.path.isdir(folder)),
        "page": page,
        "launchable": bool(entry or page),
        "python": (user.get("python") or "").strip(),
    }


def _git(folder, *args, timeout=6):
    """Output of a git command in `folder` or None (git missing, not a repo, timeout)."""
    try:
        r = subprocess.run(["git", "-C", folder, *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def read_version(info, mod_def):
    """{'version', 'tag', 'commit', 'branch', 'dirty', 'git'} of a module folder; missing pieces are ''/False.
    `version` = the number in the module's own version file when it has one, else the latest git tag."""
    out = {"version": "", "tag": "", "commit": "", "branch": "", "dirty": False, "git": False}
    folder = info["folder"]
    if not info["exists"]:
        return out
    vf = mod_def.get("version_file")
    if vf:
        try:
            text = open(os.path.join(folder, vf), encoding="utf-8").read()
            m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
            if m:
                out["version"] = m.group(1)
        except OSError:
            pass
    top = _git(folder, "rev-parse", "--show-toplevel")
    own = bool(top) and os.path.normcase(os.path.realpath(top)) == os.path.normcase(os.path.realpath(folder))      # not the repo around it
    commit = _git(folder, "rev-parse", "--short", "HEAD") if own else None
    if commit is not None:
        out["git"] = True
        out["commit"] = commit
        out["branch"] = _git(folder, "rev-parse", "--abbrev-ref", "HEAD") or ""
        out["tag"] = _git(folder, "describe", "--tags", "--abbrev=0") or ""
        out["dirty"] = bool(_git(folder, "status", "--porcelain", "--untracked-files=no"))
        if not out["version"]:
            out["version"] = out["tag"]
    return out


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


def build_command(info):
    """The full command to start a module (python command + its start file), or None when it has no start file."""
    if not info["launchable"] or not info["entry_exists"] or info.get("page") or not info.get("entry_path"):
        return None
    return python_command(info["python"]) + [info["entry_path"]]
