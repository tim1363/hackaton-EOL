import unittest

import numpy as np

from policy_observation import DEFAULT_POSE, observation


class ObservationTest(unittest.TestCase):
    def test_identity_and_layout(self):
        result = observation([1, 0, 0, 0], [1, 2, 3], DEFAULT_POSE,
                             np.arange(12), DEFAULT_POSE, [0.4, 0, 0])
        self.assertEqual(result.shape, (45,))
        np.testing.assert_allclose(result[:6], [1, 2, 3, 0, 0, -1])
        np.testing.assert_allclose(result[6:18], 0)
        np.testing.assert_allclose(result[18:30], np.arange(12))
        np.testing.assert_allclose(result[30:42], 0)
        np.testing.assert_allclose(result[42:], [0.4, 0, 0])

    def test_quaternion_rotation(self):
        h = np.sqrt(0.5)
        result = observation([h, h, 0, 0], [0]*3, DEFAULT_POSE,
                             [0]*12, DEFAULT_POSE, [0]*3)
        np.testing.assert_allclose(result[3:6], [0, -1, 0], atol=1e-6)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            observation([0]*4, [0]*3, DEFAULT_POSE, [0]*12, DEFAULT_POSE, [0]*3)
        with self.assertRaises(ValueError):
            observation([1, 0, 0, 0], [float('nan'), 0, 0], DEFAULT_POSE,
                        [0]*12, DEFAULT_POSE, [0]*3)


if __name__ == "__main__":
    unittest.main()
