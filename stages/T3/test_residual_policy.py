import unittest
from pathlib import Path

import numpy as np

from residual_policy import ResidualPolicy


class ExportTests(unittest.TestCase):
    def test_weights_match_training_actor(self):
        folder = Path(__file__).with_name("weights")
        policy = ResidualPolicy(folder)
        with np.load(folder / "parity.npz", allow_pickle=False) as fixture:
            np.testing.assert_allclose(policy.action(fixture["observations"]), fixture["actions"],
                                       rtol=1e-4, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
