"""Unit tests of pkt.shared: handing a model to PKT Analyze."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkt import shared as S  # noqa: E402


def touch(path, data=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


class AnalyzeModel(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp(prefix="pkt_am_")
        self.model = os.path.join(tmp, "best.pt")
        touch(self.model)

    def test_set_get_and_clear(self):
        st = {}
        self.assertTrue(S.set_analyze_model(st, self.model))
        self.assertEqual(S.get_analyze_model(st), os.path.normpath(self.model))
        self.assertFalse(S.set_analyze_model(st, ""))
        self.assertEqual(S.get_analyze_model(st), "")
        self.assertFalse(S.set_analyze_model(st, self.model + ".missing"))
        self.assertEqual(S.get_analyze_model(st), "")

    def test_a_model_that_was_deleted_is_not_used(self):
        st = {}
        S.set_analyze_model(st, self.model)
        os.remove(self.model)
        self.assertEqual(S.get_analyze_model(st), "")
        self.assertNotIn("PKT_MODEL_PATH", S.analyze_environment(st, base_env={}))

    def test_environment_for_analyze(self):
        st = {}
        S.set_analyze_model(st, self.model)
        env = S.analyze_environment(st, base_env={"A": "1"})
        self.assertEqual((env["A"], env["PKT_MODEL_PATH"]), ("1", os.path.normpath(self.model)))
        self.assertNotIn("PKT_MODEL_PATH", S.analyze_environment({}, base_env={"PKT_MODEL_PATH": "stale"}))      # no stale value from the shell


if __name__ == "__main__":
    unittest.main()
