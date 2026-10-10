"""Make the portable zip of PK Transport: this app + PKT Data + PKT Train + PKT Analyze (the files git tracks, nothing else:
no .git, no models, no videos, no settings), ready to send to another PC.  The other person unzips it and double-clicks install.bat.

Run from the PK-Transport folder:   py -3.12 make_portable.py            (writes dist/PK-Transport-<version>-portable.zip)
Optional: --out <file.zip>
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
REPOS = [(".", "."), ("PKT-Data", "PKT-Data"), ("PKT-Train", "PKT-Train"), (os.path.join("PKT-Analyze", "Run"), os.path.join("PKT-Analyze", "Run"))]
SKIP_SUFFIXES = (".pt", ".pth", ".engine", ".onnx", ".mp4", ".avi", ".mov", ".zip")      # weights and videos are never packed
SKIP_PARTS = ("_backups", "_git_backup", "_original_colab_versions", "pkt_settings.json")


def tracked_files(repo_dir):
    """The files git tracks (or would track: new, not ignored) in `repo_dir` (relative paths), minus weights / videos / backups."""
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=repo_dir, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    files = []
    for rel in out.split("\0"):
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
            if not os.path.isdir(repo_dir) or not os.path.isdir(os.path.join(repo_dir, ".git")) and folder != ".":
                missing.append(folder)
                continue
            for rel in tracked_files(repo_dir):
                if folder == "." and rel.split("/")[0] in ("PKT-Data", "PKT-Train", "PKT-Analyze"):
                    continue
                arc = "/".join([top] + [p for p in os.path.normpath(os.path.join(inside, rel)).split(os.sep) if p != "."])
                z.write(os.path.join(repo_dir, rel), arc)
                count += 1
    return count, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", f"PK-Transport-{__version__}-portable.zip"))
    args = ap.parse_args()
    count, missing = build(args.out)
    size = os.path.getsize(args.out) / 1e6
    print(f"{args.out}  ({count} files, {size:.1f} MB)")
    if missing:
        print("WARNING - not packed (folder or git repo not found): " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
