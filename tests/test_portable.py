"""Unit test of make_portable.py with temporary git repos: only wanted files are packed, in the right folders."""
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import make_portable as MP  # noqa: E402


def make_repo(folder, files):
    os.makedirs(folder, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=folder, check=True)
    for rel, data in files.items():
        path = os.path.join(folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    subprocess.run(["git", "add", "-A"], cwd=folder, check=True)


class Portable(unittest.TestCase):
    def test_packs_the_app_and_the_modules_without_weights_or_git(self):
        root = tempfile.mkdtemp(prefix="pkt_pz_")
        make_repo(root, {"main.py": b"app", ".gitignore": b"/PKT-Data/\n", "install.bat": b"x", "best.pt": b"w", "_backups/old.txt": b"o"})
        make_repo(os.path.join(root, "PKT-Data"), {"main.py": b"data", "src/a.py": b"a", "model.pth": b"w", "clip.mp4": b"v"})
        out = os.path.join(root, "dist", "p.zip")
        count, missing = MP.build(out, root=root, repos=[(".", "."), ("PKT-Data", "PKT-Data"), ("PKT-Train", "PKT-Train")])
        names = sorted(zipfile.ZipFile(out).namelist())
        self.assertEqual(names, ["PK-Transport/.gitignore", "PK-Transport/PKT-Data/main.py", "PK-Transport/PKT-Data/src/a.py",
                                 "PK-Transport/install.bat", "PK-Transport/main.py"])
        self.assertEqual(count, 5)
        self.assertEqual(missing, ["PKT-Train"])                       # a module that is not there is reported

    def test_a_module_folder_without_its_own_repo_is_walked(self):
        root = tempfile.mkdtemp(prefix="pkt_pz2_")
        make_repo(root, {"main.py": b"app", ".gitignore": b"/PKT-Analyze/\n"})
        folder = os.path.join(root, "PKT-Analyze")                      # inside the outer repo, ignored by it, no .git of its own
        for rel, data in {"PKStudio.py": b"a", "tools/t.py": b"t", "__pycache__/x.pyc": b"c", "best.pt": b"w", "_ort_directml/dll": b"d"}.items():
            os.makedirs(os.path.dirname(os.path.join(folder, rel)), exist_ok=True)
            with open(os.path.join(folder, rel), "wb") as f:
                f.write(data)
        out = os.path.join(root, "dist", "q.zip")
        MP.build(out, root=root, repos=[(".", "."), ("PKT-Analyze", "PKT-Analyze")])
        self.assertEqual(sorted(zipfile.ZipFile(out).namelist()),
                         ["PK-Transport/.gitignore", "PK-Transport/PKT-Analyze/PKStudio.py", "PK-Transport/PKT-Analyze/tools/t.py", "PK-Transport/main.py"])


if __name__ == "__main__":
    unittest.main()
