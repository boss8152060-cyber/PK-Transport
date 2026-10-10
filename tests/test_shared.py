"""Unit tests of pkt.shared: finding the trained runs of PKT Train and handing a model to PKT Analyze."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkt import shared as S  # noqa: E402


def touch(path, data=b"x", mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    if mtime:
        os.utime(path, (mtime, mtime))


def write_results(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("epoch,train/box_loss,metrics/mAP50(B),metrics/mAP50-95(B)\n")
        for e, a, b in rows:
            f.write(f"{e},1.0,{a},{b}\n")


def make_runs():
    root = tempfile.mkdtemp(prefix="pkt_runs_")
    now = time.time()
    r1 = os.path.join(root, "Runs", "YOLO26", "models_yolo26l", "run1")
    touch(os.path.join(r1, "weights", "best.pt"), mtime=now - 1000)
    touch(os.path.join(r1, "weights", "BEST_EPOCH_3.txt"), b"")
    write_results(os.path.join(r1, "results.csv"), [(1, 0.2, 0.1), (2, 0.4, 0.2), (3, 0.9, 0.7), (4, 0.8, 0.6), (5, 0.7, 0.5)])
    r2 = os.path.join(root, "Runs", "YOLO26", "models_yolo26l", "run2")                  # started, no best weights yet
    touch(os.path.join(r2, "weights", "last.pt"))
    r3 = os.path.join(root, "Runs", "RTDETRv2", "models_rtdetrv2_r50vd_m", "run1")
    touch(os.path.join(r3, "weights", "best.pth"), mtime=now - 10)
    r4 = os.path.join(root, "Runs", "RT-DETR", "models_rtdetr-l", "run7")                 # no results.csv, no BEST_EPOCH marker
    touch(os.path.join(r4, "weights", "best.pt"), mtime=now - 500)
    return root


class Runs(unittest.TestCase):
    def setUp(self):
        self.root = make_runs()

    def test_finds_runs_with_best_weights_newest_first(self):
        runs = S.find_runs(os.path.join(self.root, "Runs"))
        self.assertEqual([(r["family"], r["run"]) for r in runs],
                         [("RTDETRv2", "run1"), ("RT-DETR", "run7"), ("YOLO26", "run1")])          # run2 has no best weights

    def test_metrics_come_from_the_best_epoch(self):
        yolo = next(r for r in S.find_runs(os.path.join(self.root, "Runs")) if r["family"] == "YOLO26")
        self.assertEqual((yolo["best_epoch"], yolo["epochs_done"], yolo["model"]), (3, 5, "yolo26l"))
        self.assertAlmostEqual(yolo["map50"], 0.9)
        self.assertAlmostEqual(yolo["map50_95"], 0.7)
        self.assertTrue(yolo["usable_in_analyze"] and yolo["weights"].endswith("best.pt"))

    def test_run_without_results_has_no_metrics(self):
        r = next(r for r in S.find_runs(os.path.join(self.root, "Runs")) if r["run"] == "run7")
        self.assertIsNone(r["map50"])
        self.assertIsNone(r["best_epoch"])
        self.assertEqual(r["epochs_done"], 0)

    def test_pth_is_listed_but_not_usable_in_analyze(self):
        r = next(r for r in S.find_runs(os.path.join(self.root, "Runs")) if r["family"] == "RTDETRv2")
        self.assertFalse(r["usable_in_analyze"])
        self.assertTrue(r["weights"].endswith("best.pth"))

    def test_scanning_a_family_folder_and_missing_folders(self):
        only = S.find_runs(os.path.join(self.root, "Runs", "YOLO26"))
        self.assertEqual([r["run"] for r in only], ["run1"])
        self.assertEqual(S.find_runs(os.path.join(self.root, "nope")), [])
        self.assertEqual(S.find_runs(""), [])

    def test_runs_root_for(self):
        fam = os.path.join(self.root, "Runs", "YOLO26")
        self.assertEqual(S.runs_root_for(fam), os.path.join(self.root, "Runs"))
        other = os.path.join(self.root, "somewhere")
        self.assertEqual(S.runs_root_for(other), other)


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
