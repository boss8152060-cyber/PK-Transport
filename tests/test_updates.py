"""Unit tests of pkt.updates with real (temporary) git repositories: a bare 'GitHub', a clone the app watches, a second clone that pushes."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkt import updates as U  # noqa: E402


def git(folder, *args):
    return subprocess.run(["git", "-C", folder, *args], check=True, capture_output=True, text=True).stdout.strip()


def commit_file(folder, name, text, msg):
    with open(os.path.join(folder, name), "w") as f:
        f.write(text)
    git(folder, "add", name)
    git(folder, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-q", "-m", msg)


class World:
    """origin (bare) + `mine` (watched clone) + `other` (a second clone that can push)."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="pkt_upd_")
        self.origin = os.path.join(self.tmp, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        self.other = os.path.join(self.tmp, "other")
        subprocess.run(["git", "clone", "-q", self.origin, self.other], check=True, capture_output=True)
        git(self.other, "checkout", "-q", "-b", "main")
        commit_file(self.other, "a.txt", "1", "first")
        git(self.other, "push", "-q", "-u", "origin", "main")
        self.mine = os.path.join(self.tmp, "mine")
        subprocess.run(["git", "clone", "-q", self.origin, self.mine], check=True, capture_output=True)

    def push_from_other(self, name, msg):
        commit_file(self.other, name, msg, msg)
        git(self.other, "push", "-q")


class Check(unittest.TestCase):
    def test_up_to_date(self):
        w = World()
        r = U.check_repo(w.mine)
        self.assertEqual((r["state"], r["behind"], r["ahead"], r["fetched"]), ("uptodate", 0, 0, True))
        self.assertEqual(r["upstream"], "origin/main")

    def test_behind_sees_new_commits_after_a_fetch_only(self):
        w = World()
        w.push_from_other("b.txt", "second")
        self.assertEqual(U.check_repo(w.mine, fetch=False)["state"], "uptodate")      # no network: nothing known yet
        r = U.check_repo(w.mine)
        self.assertEqual((r["state"], r["behind"]), ("behind", 1))
        self.assertEqual(len(U.incoming(w.mine)), 1)
        self.assertIn("second", U.incoming(w.mine)[0])
        self.assertFalse(os.path.exists(os.path.join(w.mine, "b.txt")))              # checking changed nothing in the working copy

    def test_ahead_and_diverged(self):
        w = World()
        commit_file(w.mine, "mine.txt", "m", "local only")
        self.assertEqual(U.check_repo(w.mine)["state"], "ahead")
        w.push_from_other("c.txt", "remote")
        r = U.check_repo(w.mine)
        self.assertEqual((r["state"], r["ahead"], r["behind"]), ("diverged", 1, 1))

    def test_other_states(self):
        self.assertEqual(U.check_repo(os.path.join(tempfile.gettempdir(), "pkt_no_such_folder_x"))["state"], "missing")
        plain = tempfile.mkdtemp(prefix="pkt_plain_")
        self.assertEqual(U.check_repo(plain)["state"], "no_git")
        w = World()
        inner = os.path.join(w.mine, "PKT-Analyze")                      # a module folder inside another repo, without a .git of its own
        os.makedirs(inner)
        self.assertEqual(U.check_repo(inner, fetch=False)["state"], "no_git")           # must not answer (or pull) for the outer repo
        self.assertFalse(U.own_repo(inner))
        self.assertTrue(U.own_repo(w.mine))
        lone = tempfile.mkdtemp(prefix="pkt_lone_")
        git(lone, "init", "-q", "-b", "main")
        self.assertEqual(U.check_repo(lone)["state"], "no_upstream")

    def test_offline_fetch_failure_keeps_the_last_known_state(self):
        w = World()
        git(w.mine, "remote", "set-url", "origin", os.path.join(w.tmp, "gone.git"))
        r = U.check_repo(w.mine)
        self.assertFalse(r["fetched"])
        self.assertTrue(r["error"])
        self.assertEqual(r["state"], "uptodate")


class Pull(unittest.TestCase):
    def test_fast_forward_pull(self):
        w = World()
        w.push_from_other("b.txt", "second")
        ok, msg = U.pull_ff(w.mine)
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.isfile(os.path.join(w.mine, "b.txt")))
        self.assertEqual(U.check_repo(w.mine, fetch=False)["state"], "uptodate")

    def test_pull_refuses_to_overwrite_local_changes_and_loses_nothing(self):
        w = World()
        w.push_from_other("a.txt", "changed upstream")
        with open(os.path.join(w.mine, "a.txt"), "w") as f:
            f.write("my uncommitted work")
        U.check_repo(w.mine)
        ok, msg = U.pull_ff(w.mine)
        self.assertFalse(ok)
        self.assertTrue(msg)
        with open(os.path.join(w.mine, "a.txt")) as f:
            self.assertEqual(f.read(), "my uncommitted work")

    def test_pull_refuses_when_diverged(self):
        w = World()
        commit_file(w.mine, "mine.txt", "m", "local only")
        w.push_from_other("c.txt", "remote")
        U.check_repo(w.mine)
        ok, _msg = U.pull_ff(w.mine)
        self.assertFalse(ok)
        self.assertTrue(os.path.isfile(os.path.join(w.mine, "mine.txt")))


if __name__ == "__main__":
    unittest.main()
