"""Unit tests of the rule that decides which approaching pairs count as a TTC conflict (ttc_pair_decision) and of the clear-gap TTC of a rear-end pair."""
import math
import os
import re
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "PKStudio.py"), encoding="utf-8").read()
NS = {"math": math, "np": np, "re": re, "os": os}
exec(compile(SRC[SRC.index("# ==== CORE-BEGIN"):SRC.index("# ==== CORE-END ====")], "PKStudio.py[CORE]", "exec"), NS)
decide, clear_gap, ray = NS["ttc_pair_decision"], NS["rear_clear_gap_ttc"], NS["ray_intersection"]


def cross_of(p_a, v_a, p_b, v_b):
    return ray(p_a, v_a, p_b, v_b)


class ByType(unittest.TestCase):
    def test_a_crossing_where_both_arrive_together_counts(self):
        # A goes +x from (0, 0) at 10 m/s, B goes -y from (20, 20) at 10 m/s: both reach (20, 0) at t = 2.0 s
        c = cross_of((0, 0), (10, 0), (20, 20), (0, -10))
        self.assertAlmostEqual(c["t_a"], 2.0)
        self.assertIsNone(decide("by_type", 90.0, 0.0, 1.8, 1.8, c))

    def test_a_crossing_where_they_arrive_at_different_times_does_not(self):
        c = cross_of((0, 0), (10, 0), (20, 60), (0, -10))                # A there at 2 s, B at 6 s
        self.assertEqual(decide("by_type", 90.0, 3.0, 1.8, 1.8, c, cross_time_s=1.0), "Arrival_Time_Too_Different")
        self.assertIsNone(decide("by_type", 90.0, 3.0, 1.8, 1.8, c, cross_time_s=4.5))     # the limit is adjustable

    def test_paths_that_do_not_cross_ahead_do_not_count(self):
        self.assertEqual(decide("by_type", 60.0, 0.0, 1.8, 1.8, None), "Paths_Not_Crossing")

    def test_the_same_line_uses_the_lateral_gap_with_its_margin(self):
        # rear-end (0 deg) and head-on (180 deg) paths are parallel: no crossing to look at
        limit = (1.8 + 0.8) / 2 + 1.0
        for theta in (0.0, 12.0, 180.0, 170.0):
            self.assertIsNone(decide("by_type", theta, limit - 0.01, 1.8, 0.8, None, rear_margin=1.0), theta)
            self.assertEqual(decide("by_type", theta, limit + 0.01, 1.8, 0.8, None, rear_margin=1.0), "Lateral_Gap_Too_Large", theta)

    def test_the_angle_limit_is_the_rear_end_limit(self):
        c = cross_of((0, 0), (10, 0), (20, 20), (0, -10))
        self.assertIsNone(decide("by_type", 31.0, 99.0, 1.8, 1.8, c, rear_deg=30.0))          # a crossing: the miss distance does not matter
        self.assertEqual(decide("by_type", 29.0, 99.0, 1.8, 1.8, c, rear_deg=30.0), "Lateral_Gap_Too_Large")


class OtherModes(unittest.TestCase):
    def test_none_counts_every_approaching_pair(self):
        self.assertIsNone(decide("none", 90.0, 50.0, 1.8, 1.8, None))

    def test_miss_is_the_old_rule(self):
        self.assertIsNone(decide("miss", 90.0, 2.3, 1.8, 1.8, None, miss_margin=0.5))
        self.assertEqual(decide("miss", 90.0, 2.4, 1.8, 1.8, None, miss_margin=0.5), "Miss_Too_Far")


class ClearGap(unittest.TestCase):
    def test_bumper_to_bumper(self):
        # centres 20 m apart (the relative motion covers 20 m), two 4.5 m cars closing at 5 m/s: (20 - 4.5) / 5 = 3.1 s
        self.assertAlmostEqual(clear_gap(20.0, 5.0, 4.5, 4.5), 3.1)

    def test_already_touching_is_zero(self):
        self.assertEqual(clear_gap(3.0, 5.0, 4.5, 4.5), 0.0)

    def test_no_closing_speed_has_no_ttc(self):
        self.assertIsNone(clear_gap(20.0, 0.0, 4.5, 4.5))


if __name__ == "__main__":
    unittest.main()
