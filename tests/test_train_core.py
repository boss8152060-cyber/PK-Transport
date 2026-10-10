"""Unit tests of pkt.train_core: reading and patching the training scripts, Colab cells, progress lines."""
import ast
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pkt import train_core as TC  # noqa: E402

REAL_DIR = os.path.join(ROOT, "PKT-Train")

SAMPLE = '''"""header notes"""

# %% [Cell 1] install
import os
RUN_ENV = "auto"

# %% [Cell 2] paths
MODEL_SIZE = "l"  # @param ["n", "s", "m", "l", "x"]
PRETRAINED = f"yolo26{MODEL_SIZE}.pt"

# %% [Cell 6] train
training_mode = "auto"  # @param ["auto", "new", "continue_from_run"]
source_run_name = "run9"  # @param {type:"string"}
epochs = 300       # @param {type:"integer"}
imgsz = 640        # @param {type:"integer"}
batch = 48         # @param {type:"integer"}
workers = 24       # @param {type:"integer"}
patience = 15      # @param {type:"integer"}
lr0 = 0.0001           # @param {type:"number"}
'''


class Families(unittest.TestCase):
    def test_table(self):
        self.assertEqual(TC.FAMILY_ORDER, ["yolo26", "rtdetr", "rtdetrv2"])
        self.assertEqual(TC.FAMILIES["yolo26"]["sizes"], ["n", "s", "m", "l", "x"])
        self.assertEqual(TC.FAMILIES["rtdetr"]["sizes"], ["l", "x"])
        self.assertEqual(TC.FAMILIES["rtdetrv2"]["sizes"], ["s", "m*", "m", "l", "x"])
        for fam in TC.FAMILIES.values():
            self.assertIn(fam["default_size"], fam["sizes"])


class Patch(unittest.TestCase):
    def test_read_defaults(self):
        d = TC.read_defaults(SAMPLE)
        self.assertEqual((d["epochs"], d["imgsz"], d["batch"], d["workers"], d["patience"]), (300, 640, 48, 24, 15))
        self.assertEqual((d["model_size"], d["training_mode"], d["source_run_name"]), ("l", "auto", "run9"))

    def test_patch_writes_values_and_keeps_the_rest_of_the_line(self):
        new, missing = TC.patch_text(SAMPLE, {"epochs": 5, "batch": 2, "model_size": "x", "training_mode": "new", "source_run_name": "run3"})
        self.assertEqual(missing, [])
        self.assertIn('epochs = 5       # @param {type:"integer"}', new)       # the Colab form comment stays
        self.assertIn("batch = 2         # @param", new)
        self.assertIn('MODEL_SIZE = "x"  # @param ["n", "s", "m", "l", "x"]', new)
        self.assertIn('training_mode = "new"  # @param', new)
        self.assertIn('source_run_name = "run3"', new)
        self.assertIn("imgsz = 640", new)                                      # not asked: unchanged
        self.assertIn("lr0 = 0.0001", new)                                     # not one of the page's settings
        self.assertEqual(TC.read_defaults(new)["epochs"], 5)

    def test_missing_keys_are_reported(self):
        new, missing = TC.patch_text("epochs = 3\n", {"epochs": 9, "imgsz": 320, "model_size": "s"})
        self.assertEqual(sorted(missing), ["imgsz", "model_size"])
        self.assertIn("epochs = 9", new)

    def test_blank_values_are_ignored(self):
        new, missing = TC.patch_text(SAMPLE, {"epochs": "", "batch": None})
        self.assertEqual(new, SAMPLE)
        self.assertEqual(missing, [])


class Cells(unittest.TestCase):
    def test_cell_numbers_and_extraction(self):
        self.assertEqual(TC.cell_numbers(SAMPLE), [1, 2, 6])
        c2 = TC.extract_cell(SAMPLE, 2)
        self.assertTrue(c2.startswith("# %% [Cell 2]") and "PRETRAINED" in c2 and "Cell 6" not in c2)
        self.assertIsNone(TC.extract_cell(SAMPLE, 9))
        everything = TC.extract_cells_from(SAMPLE, 1)
        self.assertTrue(everything.startswith("# %% [Cell 1]") and "header notes" not in everything and "lr0" in everything)
        self.assertIsNone(TC.extract_cells_from("no cells", 1))


class Progress(unittest.TestCase):
    def test_lines(self):
        self.assertEqual(TC.parse_progress("      Epoch    GPU_mem   box_loss"), None)
        self.assertEqual(TC.parse_progress("        3/300     2.4G      1.234"), (3, 300))
        self.assertEqual(TC.parse_progress("  [backup] เซฟ weights ... (epoch 7)"), (7, None))
        self.assertEqual(TC.parse_progress("  [epoch 12/150] train(giou=1) mAP50=0.5"), (12, 150))
        self.assertIsNone(TC.parse_progress("Using 3 dataloader workers"))


class RunSetup(unittest.TestCase):
    def test_env_flag_and_run_script(self):
        env = TC.build_env("yolo26", "m", r"D:\data", r"D:\runs\YOLO26", base_env={"A": "1"})
        self.assertEqual((env["A"], env["PKT_MODEL_SIZE"], env["PKT_DATASET_DIR"], env["PKT_STORE_DIR"]), ("1", "m", r"D:\data", r"D:\runs\YOLO26"))
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")
        self.assertNotIn("PKT_DATASET_DIR", TC.build_env("yolo26", "m", "", "", base_env={}))
        self.assertEqual(TC.stop_flag_path("X"), os.path.join("X", "STOP.flag"))
        tmp = tempfile.mkdtemp(prefix="pkt_tc_")
        with open(os.path.join(tmp, TC.FAMILIES["yolo26"]["script"]), "w", encoding="utf-8") as f:
            f.write(SAMPLE)
        path, missing = TC.write_run_script(tmp, "yolo26", {"epochs": 2}, "T1")
        self.assertEqual(missing, [])
        self.assertTrue(path.startswith(os.path.join(tmp, "_workspace", "_gui_runs")))
        self.assertIn("epochs = 2 ", TC.read_text(path))
        self.assertIn("epochs = 300 ", TC.read_text(os.path.join(tmp, TC.FAMILIES["yolo26"]["script"])))   # the original is untouched
        self.assertEqual(TC.default_store_dir(tmp, "rtdetrv2"), os.path.join(tmp, "Runs", "RTDETRv2"))


@unittest.skipUnless(os.path.isdir(REAL_DIR), "PKT-Train is not next to this app")
class RealScripts(unittest.TestCase):
    def test_every_script_can_be_read_patched_and_split(self):
        for family in TC.FAMILY_ORDER:
            path = TC.script_path(REAL_DIR, family)
            if not os.path.isfile(path):
                self.skipTest(f"{family}: script missing")
            text = TC.read_text(path)
            d = TC.read_defaults(text)
            for key in TC.NUMERIC_KEYS + ["model_size", "training_mode"]:
                self.assertIn(key, d, (family, key))
            self.assertIn(d["model_size"], TC.FAMILIES[family]["sizes"], family)
            settings = {"model_size": TC.FAMILIES[family]["sizes"][0], "epochs": 3, "imgsz": 320, "batch": 2, "workers": 1,
                        "patience": 2, "training_mode": "new"}
            new, missing = TC.patch_text(text, settings)
            self.assertEqual(missing, [], family)
            ast.parse(new)                                                      # the patched script is still valid Python
            self.assertEqual(TC.read_defaults(new)["epochs"], 3)
            self.assertEqual(TC.read_defaults(new)["model_size"], settings["model_size"])
            self.assertEqual(TC.cell_numbers(text), list(range(1, 10)), family)
            cells = TC.extract_cells_from(new, 1)
            ast.parse(cells)                                                    # what is pasted into Colab is valid Python too
            self.assertNotIn("\n!", cells)                                      # no notebook magic left (it would break a .py run)


if __name__ == "__main__":
    unittest.main()
