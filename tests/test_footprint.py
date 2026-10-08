"""Unit tests of the vehicle rectangle placed at the reference point (footprint_offset) and of the rectangle-based PET area
(conflict_parallelogram, passage_interval) on cases with known answers."""
import math
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "PKStudio.py"), encoding="utf-8").read()
NS = {"math": math, "np": np}
import re
NS["re"] = re
exec(compile(SRC[SRC.index("# ==== CORE-BEGIN"):SRC.index("# ==== CORE-END ====")], "PKStudio.py[CORE]", "exec"), NS)
footprint_offset, conflict_parallelogram, passage_interval = NS["footprint_offset"], NS["conflict_parallelogram"], NS["passage_interval"]


class FootprintOffset(unittest.TestCase):
    def test_centre_anchor_is_no_offset(self):
        off = footprint_offset((1.0, 0.0), (4.5, 1.8), (0.5, 0.5))
        self.assertAlmostEqual(float(off[0]), 0.0)
        self.assertAlmostEqual(float(off[1]), 0.0)

    def test_bottom_anchor_sits_below_the_centre_by_the_extent(self):
        # a car driving to the right (+x, picture right) is 1.8 m tall in the picture: Bottom with 10 % offset (fy = 0.9) is 0.4 x 1.8 below the centre
        off = footprint_offset((1.0, 0.0), (4.5, 1.8), (0.5, 0.9))
        self.assertAlmostEqual(float(off[0]), 0.0)
        self.assertAlmostEqual(float(off[1]), 0.4 * 1.8)

    def test_a_car_driving_down_the_picture_is_4_5_m_tall(self):
        off = footprint_offset((0.0, 1.0), (4.5, 1.8), (0.5, 0.9))
        self.assertAlmostEqual(float(off[1]), 0.4 * 4.5)
        self.assertAlmostEqual(float(off[0]), 0.0)

    def test_left_anchor_and_a_rotated_picture(self):
        # the picture's right is the plane's +y and its down is -x: a car along +x then is 1.8 m wide in the picture, 4.5 m tall;
        # a Left anchor (fx = 0) is half the WIDTH (0.9 m) to the left = -y... (right = +y)
        off = footprint_offset((1.0, 0.0), (4.5, 1.8), (0.0, 0.5), right_u=(0.0, 1.0), down_u=(-1.0, 0.0))
        self.assertAlmostEqual(float(off[0]), 0.0)
        self.assertAlmostEqual(float(off[1]), -0.5 * 1.8)

    def test_diagonal_heading_uses_the_extent_of_the_rotated_rectangle(self):
        v = (math.cos(math.radians(45)), math.sin(math.radians(45)))
        bh = 4.5 * abs(math.sin(math.radians(45))) + 1.8 * abs(math.cos(math.radians(45)))
        off = footprint_offset(v, (4.5, 1.8), (0.5, 1.0))
        self.assertAlmostEqual(float(off[1]), 0.5 * bh, places=6)

    def test_arrays_give_one_offset_per_sample(self):
        R = np.array([[1.0, 0.0], [1.0, 0.0]])
        D = np.array([[0.0, 1.0], [0.0, 1.0]])
        off = footprint_offset(np.array([1.0, 0.0]), (4.5, 1.8), (0.5, 0.9), R, D)
        self.assertEqual(off.shape, (2, 2))
        self.assertAlmostEqual(float(off[1][1]), 0.72)


class ConflictParallelogram(unittest.TestCase):
    def test_two_perpendicular_strips_make_a_rectangle(self):
        poly = conflict_parallelogram((0.0, 0.0), (1.0, 0.0), 1.0, (5.0, 0.0), (0.0, 1.0), 2.0)
        self.assertEqual(poly.shape, (4, 2))
        xs, ys = sorted(set(round(v, 6) for v in poly[:, 0])), sorted(set(round(v, 6) for v in poly[:, 1]))
        self.assertEqual(xs, [3.0, 7.0])           # |x - 5| <= 2 (B's strip)
        self.assertEqual(ys, [-1.0, 1.0])          # |y| <= 1 (A's strip)

    def test_parallel_strips_have_no_crossing_area(self):
        self.assertIsNone(conflict_parallelogram((0, 0), (1, 0), 1.0, (0, 3), (1, 0.01), 1.0))

    def test_oblique_crossing_is_a_parallelogram_with_the_right_area(self):
        a = math.radians(60)
        poly = conflict_parallelogram((0, 0), (1, 0), 1.0, (0, 0), (math.cos(a), math.sin(a)), 0.5)
        # area = (2 * 1.0) * (2 * 0.5) / sin(60)
        x, y = poly[:, 0], poly[:, 1]
        area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
        self.assertAlmostEqual(area, 2.0 * 1.0 / math.sin(a), places=6)


class PassageInterval(unittest.TestCase):
    def test_front_in_and_rear_out(self):
        t = np.arange(0.0, 6.01, 0.1)
        c = np.stack([10.0 * t, np.zeros_like(t)], axis=1)          # 10 m/s along +x, centre at x = 10 t
        # area x in [20, 25], half length 2.5: front reaches 20 at centre 17.5 (t = 1.75), rear leaves 25 at centre 27.5 (t = 2.75)
        t_in, t_out = passage_interval(c, t, (1.0, 0.0), 20.0, 25.0, 2.5)
        self.assertAlmostEqual(t_in, 1.75, places=6)
        self.assertAlmostEqual(t_out, 2.75, places=6)

    def test_the_vehicle_never_leaves_the_area(self):
        t = np.arange(0.0, 2.01, 0.1)
        c = np.stack([10.0 * t, np.zeros_like(t)], axis=1)
        self.assertIsNone(passage_interval(c, t, (1.0, 0.0), 20.0, 25.0, 2.5))

    def test_a_path_that_starts_inside_gets_its_first_time(self):
        t = np.arange(0.0, 4.01, 0.1)
        c = np.stack([20.0 + 10.0 * t, np.zeros_like(t)], axis=1)
        t_in, t_out = passage_interval(c, t, (1.0, 0.0), 20.0, 25.0, 2.5)
        self.assertAlmostEqual(t_in, 0.0)
        self.assertAlmostEqual(t_out, 0.75, places=6)

    def test_two_vehicles_pet_by_rectangles(self):
        # the e2e case: cars 4.5 x 1.8 (+ 0.25 margin) crossing at right angles, 10 m/s, at the crossing at 1.5 s and 3.1 s
        t = np.arange(0.0, 6.01, 0.05)
        ca = np.stack([10.0 * t, np.zeros_like(t)], axis=1) + np.array([0.0, 0.0])
        ca[:, 0] += 0.0
        cb = np.stack([np.full_like(t, 15.0), 10.0 * (t - 3.1)], axis=1)
        ca[:, 0] = 10.0 * (t - 1.5) + 15.0
        poly = conflict_parallelogram((15.0, 0.0), (1.0, 0.0), 0.9 + 0.25, (15.0, 0.0), (0.0, 1.0), 0.9 + 0.25)
        pa, pb = poly @ np.array([1.0, 0.0]), poly @ np.array([0.0, 1.0])
        a_in, a_out = passage_interval(ca, t, (1.0, 0.0), float(pa.min()), float(pa.max()), 2.5)
        b_in, b_out = passage_interval(cb, t, (0.0, 1.0), float(pb.min()), float(pb.max()), 2.5)
        self.assertAlmostEqual(b_in - a_out, 0.87, places=2)


if __name__ == "__main__":
    unittest.main()
