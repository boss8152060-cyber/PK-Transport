"""Make the portable zip of PK Transport: this app + PKT Data + PKT Train + PKT Analyze (the files git tracks, nothing else:
no .git, no models, no videos, no settings), ready to send to another PC.  The other person unzips it and double-clicks install.bat.

Run from the PK-Transport folder:   py -3.12 make_portable.py            (writes dist/PK-Transport-<version>-portable.zip)
Optional: --out <file.zip>   --with-modules  (also put the newest release of every module into modules/, so the other PC needs
          no GitHub for the module files; its libraries are still downloaded by install.bat)
"""
import argparse
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from pkt import __version__  # noqa: E402

# (folder of the repo relative to ROOT, folder inside the zip)
REPOS = [(".", ".")]                   # one repository since 1.0.0 (PKT-Data, PKT-Train and PKT-Analyze are folders of it)
SKIP_SUFFIXES = (".pt", ".pth", ".engine", ".onnx", ".mp4", ".avi", ".mov", ".zip")      # weights and videos are never packed
SKIP_PARTS = ("_backups", "_git_backup", "_original_colab_versions", "_ort_directml", "__pycache__", ".git", ".venv", "pkt_settings.json", "logs")


def own_repo(folder):
    """True when `folder` is the top folder of its own git repo (not just a folder inside another repo)."""
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=folder, capture_output=True, text=True)
    return r.returncode == 0 and os.path.normcase(os.path.realpath(r.stdout.strip())) == os.path.normcase(os.path.realpath(folder))


def tracked_files(repo_dir):
    """The files git tracks (or would track: new, not ignored) in `repo_dir` (relative paths), minus weights / videos / backups.
    A folder that is not a repo of its own (e.g. PKT-Analyze after it was moved into PK-Transport) is walked instead."""
    if own_repo(repo_dir):
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=repo_dir, capture_output=True, check=True).stdout.decode("utf-8", "replace")
        listed = out.split("\0")
    else:
        listed = [os.path.relpath(os.path.join(d, f), repo_dir) for d, _dirs, names in os.walk(repo_dir) for f in names]
    files = []
    for rel in listed:
        if not rel or rel.lower().endswith(SKIP_SUFFIXES) or any(part in rel.replace("\\", "/").split("/") or rel == part for part in SKIP_PARTS):
            continue
        if os.path.isfile(os.path.join(repo_dir, rel)):
            files.append(rel)
    return files


def build(out_path, root=ROOT, repos=REPOS, top="PK-Transport"):
    """Write the zip; returns (number of files, list of repos that were missing)."""
    missing, count = [], 0
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, inside in repos:
            repo_dir = os.path.normpath(os.path.join(root, folder))
            if not os.path.isdir(repo_dir):
                missing.append(folder)
                continue
            for rel in tracked_files(repo_dir):
                arc = "/".join([top] + [p for p in os.path.normpath(os.path.join(inside, rel)).split(os.sep) if p != "."])
                z.write(os.path.join(repo_dir, rel), arc)
                count += 1
    return count, missing


def add_modules(zip_path, top="PK-Transport"):
    """Append the newest release of every module (downloaded from GitHub) to the zip as modules/<id>/...; returns the number of files."""
    import shutil
    import tempfile
    from pkt import modman
    tmp = tempfile.mkdtemp(prefix="pkt_portable_")
    n = 0
    try:
        with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as z:
            for mod_def in modman.load_registry():
                tags = modman.list_tags(mod_def)
                if not tags:
                    print(f"WARNING - no release of {mod_def['id']} found")
                    continue
                modman.install(tmp, mod_def, tags[0]["tag"], log=print)
                base = os.path.join(modman.modules_dir(tmp), mod_def["id"])
                for d, _dirs, files in os.walk(base):
                    for name in files:
                        full = os.path.join(d, name)
                        rel = os.path.relpath(full, modman.modules_dir(tmp)).replace(os.sep, "/")
                        z.write(full, f"{top}/modules/{rel}")
                        n += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", f"PK-Transport-{__version__}-portable.zip"))
    ap.add_argument("--with-modules", action="store_true", help="include the newest release of every module (needs the internet now)")
    args = ap.parse_args()
    count, missing = build(args.out)
    if args.with_modules:
        count += add_modules(args.out)
    size = os.path.getsize(args.out) / 1e6
    print(f"{args.out}  ({count} files, {size:.1f} MB)")
    if missing:
        print("WARNING - not packed (folder or git repo not found): " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
