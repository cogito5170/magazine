import unittest

import numpy as np

from edas.mathcore import color, errors, geometry as g, stats


class TestGeometry(unittest.TestCase):
    def test_union_area_is_not_sum(self):
        self.assertAlmostEqual(g.union_area([(0, 0, 2, 2), (1, 1, 3, 3)]), 7.0)
        self.assertAlmostEqual(g.union_area([(0, 0, 2, 2), (0, 0, 2, 2)]), 4.0)
        self.assertAlmostEqual(g.union_area([(0, 0, 10, 10)], clip=(0, 0, 5, 5)), 25.0)
        self.assertEqual(g.union_area([]), 0.0)

    def test_iou_and_distance(self):
        self.assertAlmostEqual(g.iou((0, 0, 2, 2), (1, 1, 3, 3)), 1 / 7)
        self.assertEqual(g.iou((0, 0, 1, 1), (2, 2, 3, 3)), 0.0)
        self.assertAlmostEqual(g.min_distance((0, 0, 1, 1), (4, 5, 6, 6)), 5.0)
        self.assertEqual(g.min_distance((0, 0, 2, 2), (1, 1, 3, 3)), 0.0)

    def test_cells(self):
        m = g.union_area_in_cells([(0, 0, 50, 100)], 100, 100, 2, 1)
        np.testing.assert_allclose(m, [[1.0, 0.0]])


class TestErrors(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(errors.error_value(3, 1, 2, "two_sided"), 1.0)
        self.assertEqual(errors.error_value(3, 1, 2, "min"), 0.0)
        self.assertEqual(errors.error_value(0, 1, 0.5, "min"), 4.0)
        self.assertEqual(errors.error_value(3, 1, 2, "max"), 1.0)
        self.assertIsNone(errors.error_value(3, None, 2, "max"))
        self.assertIsNone(errors.error_value(3, 1, 2, "none"))
        with self.assertRaises(ValueError):
            errors.error_value(1, 1, 0, "max")

    def test_normalisation(self):
        self.assertAlmostEqual(errors.zscore(5, 3, 2, eps=0), 1.0)
        self.assertEqual(errors.quantile_normalize(2, [1, 2, 3]), 0.5)
        self.assertIsNone(errors.quantile_normalize(2, []))


class TestStats(unittest.TestCase):
    def test_entropy(self):
        self.assertAlmostEqual(stats.shannon_entropy([1, 1, 1, 1]), 2.0)
        self.assertEqual(stats.shannon_entropy([5]), 0.0)
        self.assertIsNone(stats.shannon_entropy([0, 0]))

    def test_autocorrelation(self):
        self.assertIsNone(stats.autocorrelation([1, 1, 1], 1))            # zero denominator
        self.assertIsNone(stats.autocorrelation([1, 2, 3], 3))            # k out of range
        r = stats.autocorrelation([1, -1, 1, -1, 1, -1], 2)
        self.assertGreater(r, 0.5)

    def test_sign_changes_and_divergences(self):
        self.assertEqual(stats.sign_changes([0, 1, 0, 1, 0]), 3)
        self.assertEqual(stats.sign_changes([0, 1, 1, 2]), 0)
        self.assertAlmostEqual(stats.js_divergence([1, 0], [0, 1]), 1.0)
        self.assertAlmostEqual(stats.wasserstein1([0, 0], [1, 1]), 1.0)


class TestColor(unittest.TestCase):
    def test_contrast_extremes(self):
        self.assertAlmostEqual(color.contrast_ratio(1.0, 0.0), 21.0)
        self.assertAlmostEqual(color.contrast_ratio(0.5, 0.5), 1.0)

    def test_ciede2000_reference_pair(self):
        # Sharma, Wu & Dalal (2005) test data, pair 1
        d = color.ciede2000(np.array([50, 2.6772, -79.7751]), np.array([50, 0, -82.7485]))
        self.assertAlmostEqual(float(d), 2.0425, places=3)

    def test_luminance(self):
        self.assertAlmostEqual(float(color.relative_luminance(np.array([1.0, 1.0, 1.0]))), 1.0)
        self.assertAlmostEqual(float(color.relative_luminance(np.array([0.0, 0.0, 0.0]))), 0.0)


if __name__ == "__main__":
    unittest.main()
