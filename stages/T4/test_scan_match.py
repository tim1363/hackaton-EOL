import unittest

import numpy as np

from scan_match import (match_translation, quaternion_matrix, quaternion_multiply,
                        rotation2, yaw_of, yaw_quaternion)


class ScanMatchTest(unittest.TestCase):
    def test_translation_with_known_imu_yaw(self):
        rng = np.random.default_rng(42)
        previous = rng.uniform(-3, 3, (160, 2))
        expected = np.array([0.06, -0.04])
        yaw = 0.12
        current = (previous - expected) @ rotation2(yaw)
        actual = match_translation(previous, current, yaw)
        self.assertIsNotNone(actual)
        np.testing.assert_allclose(actual, expected, atol=1e-3)

    def test_rejects_insufficient_or_unrelated_points(self):
        self.assertIsNone(match_translation(np.zeros((5, 2)), np.zeros((5, 2)), 0.0))
        self.assertIsNone(match_translation(np.zeros((30, 2)), np.ones((30, 2)) * 10, 0.0))

    def test_quaternion_yaw_and_composition(self):
        a, b = yaw_quaternion(0.2), yaw_quaternion(-0.5)
        self.assertAlmostEqual(yaw_of(quaternion_multiply(a, b)), -0.3)
        np.testing.assert_allclose(quaternion_matrix(quaternion_multiply(a, b)),
                                   quaternion_matrix(a) @ quaternion_matrix(b), atol=1e-12)


if __name__ == '__main__':
    unittest.main()
