"""Unit tests of pkt.plugin, pkt.modman and pkt.envsetup against a fake GitHub (a local web server), so nothing touches the network."""
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pkt import envsetup, modman, plugin  # noqa: E402

REPO = "someone/PKT-Fake"
MOD = {"id": "fake", "name": "PKT Fake", "repo": REPO, "tag_regex": r"^v(\d+\.\d+\.\d+)$"}


def module_zip(version, mid="fake", min_shell="2.0.0", extra=None, api=1, top="PKT-Fake-x"):
    manifest = {"api": api, "id": mid, "name": "PKT Fake", "version": version, "min_shell": min_shell, "plugin": "pkt_plugin.py",
                "requirements": ["pyyaml"], "user_files": [".my_config.json"]}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{top}/pkt_module.json", json.dumps(manifest))
        z.writestr(f"{top}/pkt_plugin.py", f'API = 1\nVERSION = "{version}"\ndef summary(app, folder):\n    return "fake {version}"\n')
        z.writestr(f"{top}/lib_fake.py", f'X = "{version}"\n')
        for name, text in (extra or {}).items():
            z.writestr(f"{top}/{name}", text)
        z.writestr(f"{top}/../evil.txt", "no")
    return buf.getvalue()


class FakeGitHub(http.server.BaseHTTPRequestHandler):
    tags = []                 # names served by the API
    zips = {}                 # tag -> bytes

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        query = self.path.partition("?")[2]
        if path == f"/repos/{REPO}/tags":
            page = int(dict(p.split("=") for p in query.split("&")).get("page", "1"))
            names = FakeGitHub.tags[(page - 1) * 100: page * 100]
            body = json.dumps([{"name": n} for n in names]).encode()
            code = 200
        elif path.startswith(f"/{REPO}/archive/refs/tags/") and path.endswith(".zip"):
            tag = path.rsplit("/", 1)[1][:-4]
            body = FakeGitHub.zips.get(tag)
            code = 200 if body is not None else 404
            body = body if body is not None else b"not found"
        else:
            body, code = b"{}", 404
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.zip_url = cls.base + "/{repo}/archive/refs/tags/{tag}.zip"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pkt_mm_")
        FakeGitHub.tags = ["v1.0.0", "v1.10.0", "v1.2.0", "v0.9.9", "junk", "v1.2", "PKT-5.0.0"]
        FakeGitHub.zips = {"v1.0.0": module_zip("1.0.0"), "v1.2.0": module_zip("1.2.0"), "v1.10.0": module_zip("1.10.0")}

    def install(self, tag, **kw):
        return modman.install(self.root, MOD, tag, log=lambda m: None, zip_url=self.zip_url, shell_version="2.0.0", **kw)


class Versions(Base):
    def test_tags_are_filtered_and_sorted_by_version_number(self):
        tags = modman.list_tags(MOD, api_base=self.base)
        self.assertEqual([t["version"] for t in tags], ["1.10.0", "1.2.0", "1.0.0", "0.9.9"])          # 1.10.0 above 1.2.0; junk and other patterns dropped

    def test_versions_before_the_first_module_release_are_not_offered(self):
        mod = dict(MOD, min_version="1.2.0")
        self.assertEqual([t["version"] for t in modman.list_tags(mod, api_base=self.base)], ["1.10.0", "1.2.0"])

    def test_more_than_one_page_of_tags(self):
        FakeGitHub.tags = [f"v1.{i}.0" for i in range(230)]
        self.assertEqual(len(modman.list_tags(MOD, api_base=self.base)), 230)

    def test_the_answer_is_cached_for_an_hour(self):
        cache = os.path.join(self.root, "cache")
        modman.list_tags(MOD, api_base=self.base, cache_dir=cache)
        FakeGitHub.tags = ["v9.9.9"]
        self.assertEqual(modman.list_tags(MOD, api_base=self.base, cache_dir=cache)[0]["version"], "1.10.0")       # from the cache
        self.assertEqual(modman.list_tags(MOD, api_base=self.base, cache_dir=cache, ttl=0)[0]["version"], "9.9.9")  # expired

    def test_unreachable_github_is_an_error_not_a_crash(self):
        with self.assertRaises(modman.ModManError):
            modman.list_tags(MOD, api_base="http://127.0.0.1:9")


class InstallUninstall(Base):
    def test_install_switch_and_uninstall(self):
        manifest = self.install("v1.0.0")
        self.assertEqual(manifest["version"], "1.0.0")
        st = modman.installed_state(self.root, MOD, shell_version="2.0.0")
        self.assertEqual((st["installed"], st["version"], st["tag"], st["problem"]), (True, "1.0.0", "v1.0.0", ""))
        self.assertTrue(os.path.isfile(os.path.join(st["folder"], "lib_fake.py")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "modules", "evil.txt")))                 # a path leaving the folder is ignored
        # the module wrote a file of its own, then the version is switched: that file is carried over, the rest is replaced
        with open(os.path.join(st["folder"], ".my_config.json"), "w") as f:
            f.write("mine")
        with open(os.path.join(st["folder"], "garbage.txt"), "w") as f:
            f.write("old")
        self.install("v1.2.0")
        st = modman.installed_state(self.root, MOD, shell_version="2.0.0")
        self.assertEqual(st["version"], "1.2.0")
        self.assertEqual(open(os.path.join(st["folder"], ".my_config.json")).read(), "mine")
        self.assertFalse(os.path.exists(os.path.join(st["folder"], "garbage.txt")))                       # an exact copy of that version
        self.install("v1.0.0")                                                                             # going back works the same way
        self.assertEqual(modman.installed_state(self.root, MOD, shell_version="2.0.0")["version"], "1.0.0")
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "modules"))), ["fake"])                # no .old / .new leftovers
        modman.uninstall(self.root, MOD, log=lambda m: None)
        self.assertFalse(modman.installed_state(self.root, MOD)["installed"])
        with self.assertRaises(modman.ModManError):
            modman.uninstall(self.root, MOD, log=lambda m: None)

    def test_a_bad_download_leaves_the_installed_version_alone(self):
        self.install("v1.0.0")
        FakeGitHub.zips["v1.2.0"] = b"this is not a zip"
        with self.assertRaises(modman.ModManError):
            self.install("v1.2.0")
        FakeGitHub.zips["v1.10.0"] = module_zip("1.10.0", mid="other")                # a zip of another module
        with self.assertRaises(modman.ModManError):
            self.install("v1.10.0")
        with self.assertRaises(modman.ModManError):
            self.install("v7.7.7")                                                     # a tag that does not exist (404)
        st = modman.installed_state(self.root, MOD, shell_version="2.0.0")
        self.assertEqual(st["version"], "1.0.0")
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "modules"))), ["fake"])

    def test_a_module_that_needs_a_newer_shell_is_refused(self):
        FakeGitHub.zips["v1.2.0"] = module_zip("1.2.0", min_shell="9.0.0")
        with self.assertRaises(modman.ModManError) as ctx:
            self.install("v1.2.0")
        self.assertIn("9.0.0", str(ctx.exception))
        FakeGitHub.zips["v1.2.0"] = module_zip("1.2.0", api=2)
        with self.assertRaises(modman.ModManError):
            self.install("v1.2.0")
        self.assertFalse(modman.installed_state(self.root, MOD)["installed"])

    def test_update_state(self):
        tags = modman.list_tags(MOD, api_base=self.base)
        self.assertEqual(modman.update_state(modman.installed_state(self.root, MOD), tags), "")          # not installed
        self.install("v1.2.0")
        st = modman.installed_state(self.root, MOD, shell_version="2.0.0")
        self.assertEqual(modman.update_state(st, tags), "update")
        self.install("v1.10.0")
        self.assertEqual(modman.update_state(modman.installed_state(self.root, MOD, shell_version="2.0.0"), tags), "uptodate")

    def test_a_linked_folder_wins_and_is_never_deleted(self):
        dev = tempfile.mkdtemp(prefix="pkt_dev_")
        with open(os.path.join(dev, "pkt_module.json"), "w") as f:
            json.dump({"api": 1, "id": "fake", "name": "PKT Fake", "version": "3.0.0", "min_shell": "2.0.0"}, f)
        settings = {"modules": {"fake": {"path": dev}}}
        st = modman.installed_state(self.root, MOD, settings, shell_version="2.0.0")
        self.assertEqual((st["installed"], st["linked"], st["version"], st["folder"]), (True, True, "3.0.0", dev))
        self.assertEqual(modman.update_state(st, modman.list_tags(MOD, api_base=self.base)), "")         # no update offered for a development folder
        with self.assertRaises(modman.ModManError):
            modman.uninstall(self.root, MOD, log=lambda m: None)                                        # only modules/<id> is removed
        self.assertTrue(os.path.isdir(dev))


class PluginLoading(Base):
    def test_load_and_purge(self):
        self.install("v1.0.0")
        folder = modman.module_folder(self.root, MOD)[0]
        mod = plugin.load_plugin(folder, "fake")
        self.assertEqual((mod.API, mod.summary(None, folder)), (1, "fake 1.0.0"))
        import lib_fake
        self.assertEqual(lib_fake.X, "1.0.0")
        plugin.purge(folder, "fake")
        self.assertNotIn("lib_fake", sys.modules)
        self.assertNotIn("pkt_plugin_fake", sys.modules)
        self.install("v1.2.0")                                                                            # the new version loads in the same run
        mod = plugin.load_plugin(folder, "fake")
        import lib_fake as again
        self.assertEqual((mod.VERSION, again.X), ("1.2.0", "1.2.0"))
        plugin.purge(folder, "fake")

    def test_a_broken_plugin_is_reported(self):
        FakeGitHub.zips["v1.0.0"] = module_zip("1.0.0", extra={"pkt_plugin.py": "raise RuntimeError('boom')"})
        self.install("v1.0.0")
        with self.assertRaises(plugin.PluginError) as ctx:
            plugin.load_plugin(modman.module_folder(self.root, MOD)[0], "fake")
        self.assertIn("boom", str(ctx.exception))


class Environment(unittest.TestCase):
    def test_cuda_tag_from_nvidia_smi(self):
        smi = "| NVIDIA-SMI 560.94   Driver Version: 560.94   CUDA Version: 12.6 |\n NVIDIA GeForce GTX 1650"
        self.assertEqual(envsetup.cuda_tag_from_smi(smi), "cu126")
        self.assertEqual(envsetup.cuda_tag_from_smi(smi.replace("12.6", "12.5")), "cu124")
        self.assertEqual(envsetup.cuda_tag_from_smi(smi.replace("12.6", "11.8")), "cu118")
        self.assertEqual(envsetup.cuda_tag_from_smi("NVIDIA but no version"), "cu124")
        self.assertIsNone(envsetup.cuda_tag_from_smi(""))

    def test_requirements_are_read_from_the_manifest_and_the_file(self):
        folder = tempfile.mkdtemp()
        with open(os.path.join(folder, "requirements.txt"), "w") as f:
            f.write("# comment\npillow\nNumPy>=1.20\n-r other.txt\n")
        reqs = envsetup.module_requirements({"requirements": ["numpy", "pyyaml"], "requirements_file": "requirements.txt"}, folder)
        self.assertEqual(reqs, ["numpy", "pyyaml", "pillow"])                                             # duplicates by name dropped

    def test_prepare_runs_torch_then_requirements_with_a_fake_pip(self):
        calls = []

        def runner(cmd, log=None):
            calls.append(cmd)
            if cmd[0] == "nvidia-smi":
                return 1, []                                                                               # no GPU
            if "import torch" in cmd[-1]:
                return (0, ["2.6.0", "False"]) if any("torch" in c and "pip" in c for c in calls[:-1]) else (1, [])
            return 0, ["ok"]

        folder = tempfile.mkdtemp()
        envsetup.prepare_module({"needs_torch": True, "requirements": ["pyyaml"]}, folder, log=lambda m: None, python="py", runner=runner)
        pips = [c for c in calls if "pip" in c]
        self.assertTrue(any("torch" in c and "https://download.pytorch.org/whl/cpu" in c for c in pips))   # CPU build, no GPU
        self.assertTrue(any("-r" in c for c in pips))
        # no torch needed: only the requirements
        calls.clear()
        envsetup.prepare_module({"requirements": ["pyyaml"]}, folder, log=lambda m: None, python="py", runner=runner)
        self.assertEqual(len([c for c in calls if "pip" in c]), 1)

    def test_a_failing_pip_is_an_error(self):
        with self.assertRaises(RuntimeError):
            envsetup.install_requirements("py", ["x"], log=lambda m: None, runner=lambda cmd: (1, ["boom"]))


if __name__ == "__main__":
    unittest.main()
