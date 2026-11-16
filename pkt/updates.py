"""Update check of the modules and of this app: is there something new on GitHub, and a safe way to take it.

Two ways, the same button: a git checkout (git clone) uses git; a folder from "Download ZIP" (no .git) compares the version number
with the one on GitHub and, on request, downloads the zip of the repository and copies its files over the app (the user's own files
are never touched: .venv, settings, logs, trained runs, data).

Only read-only git calls (fetch, rev-list, log) except pull_ff, which is a fast-forward pull: it never merges, rewrites or
discards anything of the user's (if it cannot fast-forward, git refuses and the message is shown).
"""
import io
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

REPO = "boss8152060-cyber/PK-Transport"
RAW_URL = "https://raw.githubusercontent.com/" + REPO + "/main/"
ZIP_URL = "https://github.com/" + REPO + "/archive/refs/heads/main.zip"
# never overwritten by a zip update (the user's own environment, settings, results and data)
KEEP = (".venv", "pkt_settings.json", "logs", "dist", "_backups", ".git", "__pycache__", "Runs", "_workspace", "_gui_runs", "_ort_directml")

STATES = ("uptodate", "behind", "ahead", "diverged", "no_upstream", "no_git", "missing")


def _git(folder, *args, timeout=30):
    """(returncode, stdout, stderr) of a git command in `folder`; (None, '', error) when git cannot run."""
    try:
        r = subprocess.run(["git", "-C", folder, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", str(exc)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def own_repo(folder):
    """True when `folder` is the top folder of its own git repo. A module folder without a .git of its own that sits inside another
    repo (e.g. PKT-Analyze inside PK-Transport) is NOT: git would then answer for the outer repo, and an update would pull the wrong one."""
    rc, top, _e = _git(folder, "rev-parse", "--show-toplevel")
    return rc == 0 and bool(top) and os.path.normcase(os.path.realpath(top)) == os.path.normcase(os.path.realpath(folder))


def check_repo(folder, fetch=True, timeout=40):
    """{'state', 'behind', 'ahead', 'upstream', 'fetched', 'error'} for the repo in `folder`.
    state: uptodate | behind (new commits on GitHub) | ahead (local commits not pushed) | diverged | no_upstream | no_git | missing.
    fetch=False compares with what was fetched before (no network)."""
    out = {"state": "missing", "behind": 0, "ahead": 0, "upstream": "", "fetched": False, "error": ""}
    if not folder or not os.path.isdir(folder):
        return out
    rc, _o, _e = _git(folder, "rev-parse", "--git-dir")
    if rc != 0 or not own_repo(folder):
        out["state"] = "no_git"
        return out
    rc, upstream, _e = _git(folder, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if rc != 0 or not upstream:
        out["state"] = "no_upstream"
        return out
    out["upstream"] = upstream
    if fetch:
        rc, _o, err = _git(folder, "fetch", "--quiet", timeout=timeout)
        out["fetched"] = rc == 0
        if rc != 0:
            out["error"] = err[-200:] or "fetch failed"          # offline etc.: the result below is from the last fetch
    rc, counts, err = _git(folder, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    if rc != 0 or not counts:
        out["state"] = "no_upstream"
        out["error"] = out["error"] or err[-200:]
        return out
    ahead, behind = (int(x) for x in counts.split()[:2])
    out["ahead"], out["behind"] = ahead, behind
    out["state"] = "diverged" if (ahead and behind) else "behind" if behind else "ahead" if ahead else "uptodate"
    return out


def incoming(folder, limit=8):
    """The subjects of the commits that a pull would bring (newest first), as a list of 'hash subject'."""
    rc, out, _e = _git(folder, "log", "--oneline", f"-n{int(limit)}", "HEAD..@{u}")
    return out.splitlines() if rc == 0 and out else []


def pull_ff(folder, timeout=120):
    """git pull --ff-only; returns (ok, message). Local changes that would be overwritten make git refuse (nothing is lost)."""
    rc, out, err = _git(folder, "pull", "--ff-only", timeout=timeout)
    return rc == 0, (out if rc == 0 else (err or out))[-600:]       # on a refusal git explains itself on stderr


# ====================================================================== zip update (a folder without .git)
def version_tuple(text):
    """'1.2.10' -> (1, 2, 10); anything else -> ()"""
    m = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", text or "")
    return tuple(int(x) for x in m.groups()) if m else ()


def _version_in(text):
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text or "")
    return m.group(1) if m else ""


def local_version(root):
    try:
        with open(os.path.join(root, "pkt", "__init__.py"), encoding="utf-8") as f:
            return _version_in(f.read())
    except OSError:
        return ""


def remote_version(raw_url=RAW_URL, timeout=15):
    """The version number on GitHub (pkt/__init__.py of main), or '' when it cannot be read."""
    try:
        with urllib.request.urlopen(raw_url + "pkt/__init__.py", timeout=timeout) as r:
            return _version_in(r.read().decode("utf-8", "replace"))
    except (OSError, ValueError):
        return ""


def check_zip(root, raw_url=RAW_URL, timeout=15):
    """Like check_repo, for a folder that has no .git: {'state', 'zip': True, 'local', 'remote', 'error', ...}.
    state: uptodate | behind (a higher version number on GitHub) | no_upstream (GitHub could not be read)."""
    out = {"state": "no_upstream", "behind": 0, "ahead": 0, "upstream": "", "fetched": False, "error": "", "zip": True, "local": local_version(root), "remote": ""}
    remote = remote_version(raw_url, timeout)
    if not remote or not version_tuple(remote) or not version_tuple(out["local"]):
        out["error"] = "GitHub (or the local version) could not be read"
        return out
    out["remote"], out["fetched"] = remote, True
    out["state"] = "behind" if version_tuple(remote) > version_tuple(out["local"]) else "uptodate"
    out["behind"] = 1 if out["state"] == "behind" else 0
    return out


def apply_zip(root, zip_url=ZIP_URL, timeout=120):
    """Download the zip of the repository and copy its files over `root`. Returns (ok, message).
    Only files of the repository are written (new and changed ones); nothing is deleted and KEEP folders / files are skipped."""
    try:
        with urllib.request.urlopen(zip_url, timeout=timeout) as r:
            data = r.read()
    except (OSError, ValueError) as exc:
        return False, f"download failed: {exc}"
    tmp = tempfile.mkdtemp(prefix="pkt_update_")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            top = names[0].split("/")[0] if names else ""
            if not top or not any(n == f"{top}/pkt/__init__.py" for n in names):
                return False, "the downloaded file is not PK Transport"
            written = 0
            for name in names:
                rel = name[len(top) + 1:]
                parts = [p for p in rel.split("/") if p]
                if not parts or ".." in parts or any(p in KEEP for p in parts) or os.path.isabs(rel):
                    continue
                dest = os.path.normpath(os.path.join(root, *parts))
                if os.path.commonpath([os.path.abspath(dest), os.path.abspath(root)]) != os.path.abspath(root):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(name) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                written += 1
        return True, f"{written} files updated"
    except (zipfile.BadZipFile, OSError) as exc:
        return False, str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
