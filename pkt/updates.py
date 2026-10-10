"""Update check of the modules and of this app (git): is there something new on GitHub, and a safe way to take it.

Only read-only git calls (fetch, rev-list, log) except pull_ff, which is a fast-forward pull: it never merges, rewrites or
discards anything of the user's (if it cannot fast-forward, git refuses and the message is shown).
"""
import os
import subprocess

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
