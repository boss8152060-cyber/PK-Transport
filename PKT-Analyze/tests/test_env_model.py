"""The default model of PKT Analyze can come from PKT_MODEL_PATH (set by PK Transport)."""
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "PKStudio.py"), encoding="utf-8").read()
NS = {"os": os}
exec(compile(SRC[SRC.index("# ---- PKT_ENV-BEGIN"):SRC.index("# ---- PKT_ENV-END")], "PKStudio.py[ENV]", "exec"), NS)
env_model = NS["_env_model"]


class EnvModel(unittest.TestCase):
    def test_existing_file_wins(self):
        tmp = tempfile.mkdtemp(prefix="pkt_envm_")
        f = os.path.join(tmp, "best.pt")
        with open(f, "wb") as fh:
            fh.write(b"x")
        self.assertEqual(env_model("default.pt", {"PKT_MODEL_PATH": f}), f)
        self.assertEqual(env_model("default.pt", {"PKT_MODEL_PATH": f"  {f}  "}), f)

    def test_missing_blank_or_unset_keeps_the_default(self):
        self.assertEqual(env_model("default.pt", {"PKT_MODEL_PATH": r"Z:\nope\best.pt"}), "default.pt")
        self.assertEqual(env_model("default.pt", {"PKT_MODEL_PATH": ""}), "default.pt")
        self.assertEqual(env_model("default.pt", {}), "default.pt")


if __name__ == "__main__":
    unittest.main()
