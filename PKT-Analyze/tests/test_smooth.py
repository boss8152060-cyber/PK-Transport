"""Unit tests of smooth_positions (the steadier trajectory used before every indicator)."""
import math
import os
import re
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "PKStudio.py"), encoding="utf-8").read()
NS = {"math": math, "np": np, "re": re}
exec(compile(SRC[SRC.index("# ==== CORE-BEGIN"):SRC.index("# ==== CORE-END ====")], "PKStudio.py[CORE]", "exec"), NS)
smooth_positions = NS["smooth_positions"]


def line(n=61, dt=1 / 30.0, v=(8.0, 2.0)):
    t = np.arange(n) * dt
    return t, np.stack([v[0] * t, v[1] * t], axis=1)


class SmoothPositions(unittest.TestCase):
    def test_a_straight_path_is_not_changed(self):
        t, P = line()
        for method in ("mean", "median", "median_mean"):
            out = smooth_positions(t, P, 0.3, method)
            self.assertTrue(np.allclose(out, P, atol=1e-9), method)

    def test_none_and_zero_window_return_the_input(self):
        t, P = line()
        P[10, 1] += 3.0
        self.assertTrue(np.allclose(smooth_positions(t, P, 0.3, "none"), P))
        self.assertTrue(np.allclose(smooth_positions(t, P, 0.0, "median"), P))

    def test_a_one_frame_jump_is_removed_by_the_median(self):
        t, P = line()
        noisy = P.copy()
        noisy[30] += [0.0, 2.5]                       # the box flickers for one frame
        out = smooth_positions(t, noisy, 0.3, "median")
        step = abs(P[31, 1] - P[30, 1])                  # the median is one of the neighbours: off by at most one sample of movement
        self.assertLessEqual(abs(out[30, 1] - P[30, 1]), step + 1e-9)

    def test_the_mean_only_spreads_the_jump(self):
        t, P = line()
        noisy = P.copy()
        noisy[30] += [0.0, 2.5]
        out = smooth_positions(t, noisy, 0.3, "mean")
        self.assertTrue(0.1 < out[30, 1] - P[30, 1] < 2.5)

    def test_random_wobble_gets_smaller(self):
        rng = np.random.default_rng(1)
        t, P = line(200)
        noisy = P + rng.normal(0, 0.15, P.shape)
        err_raw = np.abs(noisy - P).mean()
        err_sm = np.abs(smooth_positions(t, noisy, 0.4, "median_mean") - P).mean()
        self.assertLess(err_sm, 0.6 * err_raw)

    def test_the_window_is_in_seconds_not_samples(self):
        # at 10 fps a 0.3 s window holds 3 samples: the jump of one sample is still removed
        t, P = line(40, dt=0.1)
        noisy = P.copy()
        noisy[20] += [0.0, 2.0]
        out = smooth_positions(t, noisy, 0.3, "median")
        self.assertLessEqual(abs(out[20, 1] - P[20, 1]), abs(P[21, 1] - P[20, 1]) + 1e-9)

    def test_short_paths_and_the_ends_are_safe(self):
        t, P = line(2)
        self.assertTrue(np.allclose(smooth_positions(t, P, 0.3, "median"), P))
        t, P = line(30)
        out = smooth_positions(t, P, 5.0, "median_mean")           # a window longer than the path
        self.assertEqual(out.shape, P.shape)
        self.assertTrue(np.allclose(out, P, atol=1e-9))
        self.assertTrue(np.allclose(out[0], P[0]) and np.allclose(out[-1], P[-1]))


if __name__ == "__main__":
    unittest.main()
