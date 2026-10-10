"""Unit tests of pkt.modules (no GUI): folders, versions, start commands."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from pkt import modules as M  # noqa: E402


def git(folder, *args):
    subprocess.run(["git", "-C", folder, *args], check=True, capture_output=True)


def make_repo(folder, tag="v9.9.9"):
    os.makedirs(folder, exist_ok=True)
    git(folder, "init", "-q", "-b", "main")
    git(folder, "config", "user.email", "t@example.com")
    git(folder, "config", "user.name", "t")
    with open(os.path.join(folder, "a.txt"), "w") as f:
        f.write("a")
    git(folder, "add", "a.txt")
    git(folder, "commit", "-q", "-m", "first")
    git(folder, "tag", tag)


class Defs(unittest.TestCase):
    def test_default_modules_file_lists_the_three_modules(self):
        defs = M.load_module_defs()
        self.assertEqual([d["id"] for d in defs], ["data", "train", "analyze"])
        self.assertEqual([d["name"] for d in defs], ["PKT Data", "PKT Train", "PKT Analyze"])
        self.assertEqual(next(d for d in defs if d["id"] == "analyze")["path"], "PKT-Analyze/Run")
        self.assertIsNone(next(d for d in defs if d["id"] == "train")["entry"])


class Resolve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pkt_mod_")
        os.makedirs(os.path.join(self.tmp, "ModA"))
        with open(os.path.join(self.tmp, "ModA", "start.py"), "w") as f:
            f.write("print(1)")
        self.d = {"id": "a", "name": "A", "path": "ModA", "entry": "start.py"}

    def test_relative_folder_is_under_the_root(self):
        info = M.resolve_module(self.d, {}, self.tmp)
        self.assertEqual(info["folder"], os.path.join(self.tmp, "ModA"))
        self.assertTrue(info["exists"] and info["entry_exists"] and info["launchable"])

    def test_user_folder_wins(self):
        other = os.path.join(self.tmp, "Other")
        os.makedirs(other)
        info = M.resolve_module(self.d, {"modules": {"a": {"path": other}}}, self.tmp)
        self.assertEqual(info["folder"], other)
        self.assertTrue(info["exists"])
        self.assertFalse(info["entry_exists"])               # no start.py in the other folder

    def test_missing_folder_and_module_without_entry(self):
        info = M.resolve_module({"id": "b", "name": "B", "path": "Nope", "entry": None}, {}, self.tmp)
        self.assertFalse(info["exists"])
        self.assertFalse(info["launchable"])
        self.assertIsNone(M.build_command(info))


class Versions(unittest.TestCase):
    def test_version_from_the_file_and_git_info(self):
        tmp = tempfile.mkdtemp(prefix="pkt_ver_")
        make_repo(tmp, "v1.2.3")
        os.makedirs(os.path.join(tmp, "src"))
        with open(os.path.join(tmp, "src", "ver.py"), "w") as f:
            f.write('__version__ = "4.5.6"\n')
        info = {"folder": tmp, "exists": True}
        v = M.read_version(info, {"version_file": "src/ver.py"})
        self.assertEqual(v["version"], "4.5.6")              # the module's own number wins over the tag
        self.assertEqual((v["tag"], v["branch"], v["git"], v["dirty"]), ("v1.2.3", "main", True, False))
        self.assertTrue(v["commit"])

    def test_tag_is_the_version_without_a_file_and_dirty_is_seen(self):
        tmp = tempfile.mkdtemp(prefix="pkt_ver_")
        make_repo(tmp, "PKT-1.0.0")
        with open(os.path.join(tmp, "a.txt"), "w") as f:
            f.write("changed")
        v = M.read_version({"folder": tmp, "exists": True}, {})
        self.assertEqual(v["version"], "PKT-1.0.0")
        self.assertTrue(v["dirty"])

    def test_untracked_files_do_not_make_it_dirty(self):
        tmp = tempfile.mkdtemp(prefix="pkt_ver_")
        make_repo(tmp)
        with open(os.path.join(tmp, "new.txt"), "w") as f:
            f.write("x")
        self.assertFalse(M.read_version({"folder": tmp, "exists": True}, {})["dirty"])

    def test_not_a_repo_and_missing_folder(self):
        tmp = tempfile.mkdtemp(prefix="pkt_ver_")
        v = M.read_version({"folder": tmp, "exists": True}, {})
        self.assertFalse(v["git"])
        self.assertEqual(v["version"], "")
        self.assertEqual(M.read_version({"folder": tmp + "_x", "exists": False}, {})["version"], "")


class Command(unittest.TestCase):
    def test_python_override_is_split(self):
        self.assertEqual(M.python_command("python3 -X utf8"), ["python3", "-X", "utf8"])

    def test_quoted_python_path_with_spaces(self):
        cmd = M.python_command('"C:\Program Files\Python312\python.exe" -X utf8')
        self.assertEqual(cmd, ["C:\Program Files\Python312\python.exe", "-X", "utf8"])

    def test_automatic_command_is_a_list_ending_in_a_python(self):
        cmd = M.python_command("")
        self.assertIsInstance(cmd, list)
        self.assertTrue(cmd[0] in ("py", sys.executable))

    def test_build_command_adds_the_start_file(self):
        tmp = tempfile.mkdtemp(prefix="pkt_cmd_")
        with open(os.path.join(tmp, "s.py"), "w") as f:
            f.write("")
        info = M.resolve_module({"id": "x", "name": "X", "path": tmp, "entry": "s.py"}, {"modules": {"x": {"python": "mypy"}}}, tmp)
        self.assertEqual(M.build_command(info), ["mypy", os.path.join(tmp, "s.py")])


class VirtualEnv(unittest.TestCase):
    def test_inside_a_venv_the_modules_use_it(self):
        real_prefix = sys.prefix
        try:
            sys.prefix = os.path.join(real_prefix, "pretend_venv")
            self.assertEqual(M.python_command(""), [sys.executable])
            self.assertEqual(M.python_command("py -3.11"), ["py", "-3.11"])          # an override still wins
        finally:
            sys.prefix = real_prefix


class Settings(unittest.TestCase):
    def test_round_trip_and_bad_file(self):
        tmp = tempfile.mkdtemp(prefix="pkt_set_")
        path = os.path.join(tmp, "s.json")
        M.save_settings({"language": "en", "modules": {"a": {"path": "ไทย"}}}, path)
        self.assertEqual(M.load_settings(path)["modules"]["a"]["path"], "ไทย")
        with open(path, "w") as f:
            f.write("not json")
        self.assertEqual(M.load_settings(path), {})
        self.assertEqual(M.load_settings(os.path.join(tmp, "none.json")), {})


if __name__ == "__main__":
    unittest.main()
