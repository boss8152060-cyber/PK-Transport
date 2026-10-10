"""Unit test of pkt.shortcut: a real .lnk is made in a temporary folder (Windows only) and read back."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pkt import shortcut as SC  # noqa: E402


class Target(unittest.TestCase):
    def test_target_runs_main_py_of_the_app(self):
        program, args = SC.launcher_target(ROOT)
        self.assertTrue(program)
        self.assertIn(os.path.join(ROOT, "main.py"), args)


    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_the_private_environment_is_preferred(self):
        root = tempfile.mkdtemp(prefix="pkt_sc_venv_")
        os.makedirs(os.path.join(root, ".venv", "Scripts"))
        venv_w = os.path.join(root, ".venv", "Scripts", "pythonw.exe")
        open(venv_w, "wb").close()
        program, args = SC.launcher_target(root)
        self.assertEqual(program, venv_w)
        self.assertEqual(args, '"' + os.path.join(root, "main.py") + '"')


@unittest.skipUnless(os.name == "nt", "shortcuts are made on Windows only")
class Lnk(unittest.TestCase):
    def test_creates_a_shortcut_with_target_arguments_and_folder(self):
        out = tempfile.mkdtemp(prefix="pkt_lnk_")
        ok, path = SC.create_shortcut(ROOT, folder=out, name="PK Transport Test")
        self.assertTrue(ok, path)
        self.assertEqual(path, os.path.join(out, "PK Transport Test.lnk"))
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK); "
              "Write-Output $s.TargetPath; Write-Output $s.Arguments; Write-Output $s.WorkingDirectory")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, env=dict(os.environ, LNK=path))
        target, args, workdir = (r.stdout.strip().splitlines() + ["", "", ""])[:3]
        program, wanted_args = SC.launcher_target(ROOT)
        self.assertEqual(os.path.normcase(target), os.path.normcase(program))
        self.assertEqual(args, wanted_args)
        self.assertEqual(os.path.normcase(workdir), os.path.normcase(ROOT))

    def test_a_missing_folder_is_reported(self):
        ok, msg = SC.create_shortcut(ROOT, folder=os.path.join(tempfile.gettempdir(), "pkt_no_dir_x"), name="x")
        self.assertFalse(ok)
        self.assertTrue(msg)


if __name__ == "__main__":
    unittest.main()
