"""Unit tests of pkt.modules (settings, the Python command) and of the registry modules.json."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pkt import modman  # noqa: E402
from pkt import modules as M  # noqa: E402


class Registry(unittest.TestCase):
    def test_the_real_registry(self):
        defs = modman.load_registry(os.path.join(ROOT, "modules.json"))
        self.assertEqual([d["id"] for d in defs], ["data", "train", "analyze"])
        for d in defs:
            self.assertRegex(d["repo"], r"^[\w-]+/[\w.-]+$")
            self.assertTrue(d["tag_regex"].startswith("^") and "(" in d["tag_regex"])
            self.assertTrue(modman.parse_tags([], d["tag_regex"]) == [])
            self.assertRegex(d["min_version"], r"^\d+\.\d+\.\d+$")
            self.assertTrue(d["desc_key"])
        by_id = {d["id"]: d for d in defs}
        self.assertEqual([t["version"] for t in modman.parse_tags(["PKT-1.46.3", "PKT-1.47.0", "v28-95", "PKT-1.10.0", "PKT-1.47.1"], by_id["analyze"]["tag_regex"], by_id["analyze"]["min_version"])],
                         ["1.47.1", "1.47.0"])                                             # Analyze tags are written PKT-x.y.z; older ones are not modules
        self.assertEqual([t["version"] for t in modman.parse_tags(["v1.3.8", "v1.4.0", "v1.10.0"], by_id["data"]["tag_regex"], by_id["data"]["min_version"])], ["1.10.0", "1.4.0"])

    def test_a_missing_registry_is_an_error(self):
        with self.assertRaises(modman.ModManError):
            modman.load_registry(os.path.join(tempfile.gettempdir(), "pkt_no_registry.json"))


class Settings(unittest.TestCase):
    def test_load_save_round_trip(self):
        path = os.path.join(tempfile.mkdtemp(), "s.json")
        self.assertEqual(M.load_settings(path), {})                                         # missing file
        M.save_settings({"language": "th", "x": [1]}, path)
        self.assertEqual(M.load_settings(path), {"language": "th", "x": [1]})
        with open(path, "w") as f:
            f.write("not json")
        self.assertEqual(M.load_settings(path), {})                                         # damaged file: start fresh, no crash
        with open(path, "w") as f:
            f.write("[1, 2]")
        self.assertEqual(M.load_settings(path), {})


class Command(unittest.TestCase):
    def test_override_is_split_and_quotes_are_stripped(self):
        self.assertEqual(M.python_command("py -3.12"), ["py", "-3.12"])
        self.assertEqual(M.python_command('"C:\\Program Files\\Python312\\python.exe" -u'), ["C:\\Program Files\\Python312\\python.exe", "-u"])

    def test_inside_a_venv_this_python_is_used(self):
        real = sys.prefix
        try:
            sys.prefix = os.path.join(real, "pretend_venv")
            self.assertEqual(M.python_command(""), [sys.executable])
        finally:
            sys.prefix = real


if __name__ == "__main__":
    unittest.main()
