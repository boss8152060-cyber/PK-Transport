"""Unit tests of the frame-rate / size helpers of the result videos (output_fps_ratio, output_frame_offset, topview_px_setting)."""
import math
import os
import re
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "PKStudio.py"), encoding="utf-8").read()
NS = {"math": math, "np": np, "re": re, "os": os}
exec(compile(SRC[SRC.index("# ==== CORE-BEGIN"):SRC.index("# ==== CORE-END ====")], "PKStudio.py[CORE]", "exec"), NS)
ratio, offset, px = NS["output_fps_ratio"], NS["output_frame_offset"], NS["topview_px_setting"]


class FpsRatio(unittest.TestCase):
    def test_blank_zero_bad_or_not_lower_keeps_every_frame(self):
        for t in ("", "0", "abc", "60", "75", None):
            self.assertEqual(ratio(t, 60.0), 1.0, t)
        self.assertEqual(ratio("30", 0), 1.0)
        self.assertEqual(ratio("30", None), 1.0)

    def test_lower_rate_is_the_share_kept(self):
        self.assertAlmostEqual(ratio("30", 60.0), 0.5)
        self.assertAlmostEqual(ratio("25", 60.0), 25 / 60.0)


class FrameOffset(unittest.TestCase):
    def test_every_frame(self):
        self.assertEqual([offset(i, 1.0) for i in range(4)], [0, 1, 2, 3])

    def test_half(self):
        self.assertEqual([offset(i, 0.5) for i in range(4)], [0, 2, 4, 6])

    def test_uneven_share_spreads_the_kept_frames(self):
        r = 25 / 60.0
        k = [offset(i, r) for i in range(6)]
        self.assertEqual(k[0], 0)
        self.assertTrue(all(b > a for a, b in zip(k, k[1:])))
        self.assertTrue(all(b - a in (2, 3) for a, b in zip(k, k[1:])))                 # 2.4 frames apart on average
        self.assertAlmostEqual(k[5] / 5.0, 1 / r, delta=0.5)

    def test_the_writer_loop_and_the_overlay_agree(self):
        # the writer keeps a frame when (frame offset) >= offset(written so far); the overlay reads back frame offset(i)
        r = 0.4
        kept, written = [], 0
        for k in range(40):
            if k >= offset(written, r):
                kept.append(k)
                written += 1
        self.assertEqual(kept, [offset(i, r) for i in range(len(kept))])


class TopviewPx(unittest.TestCase):
    def test_values(self):
        self.assertEqual(px("960"), 960)
        self.assertEqual(px(" 1600 "), 1600)
        for t in ("", "0", "-5", "x"):
            self.assertEqual(px(t), 1280, t)
        self.assertEqual(px("", 800), 800)


if __name__ == "__main__":
    unittest.main()
