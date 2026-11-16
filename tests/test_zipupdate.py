"""Unit test of the zip update (a folder from "Download ZIP" has no .git): version check and copying the new files, against a local web server."""
import http.server
import os
import sys
import tempfile
import threading
import unittest
import zipfile
from functools import partial

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pkt import updates as U  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class ZipUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = tempfile.mkdtemp(prefix="pkt_web_")
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=cls.web)
        handler.log_message = lambda *a, **k: None
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def make_remote(self, version="9.9.9", extra=None):
        write(os.path.join(self.web, "pkt", "__init__.py"), f'__version__ = "{version}"\n')
        with zipfile.ZipFile(os.path.join(self.web, "main.zip"), "w") as z:
            z.writestr("PK-Transport-main/pkt/__init__.py", f'__version__ = "{version}"\n')
            z.writestr("PK-Transport-main/main.py", "print('new')\n")
            z.writestr("PK-Transport-main/PKT-Data/new_file.py", "x = 1\n")
            z.writestr("PK-Transport-main/pkt_settings.json", '{"language": "from zip"}')           # must never overwrite the user's
            z.writestr("PK-Transport-main/PKT-Train/Runs/a.pt", "weights")                          # nor touch a trained run
            z.writestr("PK-Transport-main/../evil.txt", "no")
            for name, data in (extra or {}).items():
                z.writestr("PK-Transport-main/" + name, data)

    def make_local(self, version="1.0.0"):
        root = tempfile.mkdtemp(prefix="pkt_app_")
        write(os.path.join(root, "pkt", "__init__.py"), f'__version__ = "{version}"\n')
        write(os.path.join(root, "main.py"), "print('old')\n")
        write(os.path.join(root, "pkt_settings.json"), '{"language": "mine"}')
        write(os.path.join(root, ".venv", "keep.txt"), "venv")
        return root

    def test_version_numbers(self):
        self.assertGreater(U.version_tuple("1.10.0"), U.version_tuple("1.9.9"))
        self.assertEqual(U.version_tuple("x"), ())
        self.assertEqual(U.local_version(self.make_local("2.3.4")), "2.3.4")

    def test_check_then_update_then_up_to_date(self):
        self.make_remote("9.9.9")
        root = self.make_local("1.0.0")
        res = U.check_zip(root, raw_url=self.base)
        self.assertEqual((res["state"], res["local"], res["remote"], res["zip"]), ("behind", "1.0.0", "9.9.9", True))
        ok, msg = U.apply_zip(root, zip_url=self.base + "main.zip")
        self.assertTrue(ok, msg)
        self.assertEqual(open(os.path.join(root, "main.py")).read(), "print('new')\n")                 # changed file replaced
        self.assertTrue(os.path.isfile(os.path.join(root, "PKT-Data", "new_file.py")))                  # new file added
        self.assertEqual(open(os.path.join(root, "pkt_settings.json")).read(), '{"language": "mine"}')  # settings kept
        self.assertEqual(open(os.path.join(root, ".venv", "keep.txt")).read(), "venv")
        self.assertFalse(os.path.exists(os.path.join(root, "PKT-Train", "Runs", "a.pt")))               # trained runs are never written
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(root), "evil.txt")))               # a path leaving the folder is ignored
        self.assertEqual(U.check_zip(root, raw_url=self.base)["state"], "uptodate")

    def test_same_version_is_up_to_date_and_unreachable_is_reported(self):
        self.make_remote("1.0.0")
        self.assertEqual(U.check_zip(self.make_local("1.0.0"), raw_url=self.base)["state"], "uptodate")
        res = U.check_zip(self.make_local("1.0.0"), raw_url="http://127.0.0.1:9/")
        self.assertEqual((res["state"], bool(res["error"])), ("no_upstream", True))

    def test_a_zip_that_is_not_pk_transport_is_refused(self):
        with zipfile.ZipFile(os.path.join(self.web, "other.zip"), "w") as z:
            z.writestr("something/readme.txt", "x")
        root = self.make_local()
        ok, msg = U.apply_zip(root, zip_url=self.base + "other.zip")
        self.assertFalse(ok)
        self.assertEqual(open(os.path.join(root, "main.py")).read(), "print('old')\n")                  # nothing changed


if __name__ == "__main__":
    unittest.main()
