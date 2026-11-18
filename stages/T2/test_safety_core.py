"""Safety-core regression tests; optional original model parity via GO1_FULL_SCENE."""
import os
import time
import unittest

import mujoco
import numpy as np

from safety_core import CollisionChecker, HOME, LOWER, MAX_STEP, TargetFilter, UPPER


class SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = CollisionChecker()

    def test_home_and_target_filter(self):
        self.assertTrue(self.checker.safe(HOME))
        f = TargetFilter(self.checker)
        q, accepted = f.apply(HOME + 0.01)
        self.assertTrue(accepted)
        np.testing.assert_allclose(q, HOME + 0.01)
        old = q.copy()
        q, accepted = f.apply(np.full(12, np.nan))
        self.assertFalse(accepted)
        np.testing.assert_array_equal(q, old)
        q, _ = f.apply(np.full(12, 1000.0))
        self.assertLessEqual(np.max(np.abs(q - old)), MAX_STEP + 1e-12)
        self.assertTrue(np.all((q >= LOWER) & (q <= UPPER)))

    def test_collision_found_and_rejected(self):
        rng = np.random.default_rng(47)
        for _ in range(1000):
            q = rng.uniform(LOWER, UPPER)
            if not self.checker.safe(q):
                break
        else:
            self.fail("No collision found in 1000 random joint configurations")
        with self.assertRaises(ValueError):
            TargetFilter(self.checker, q)
        self.assertFalse(self.checker.safe_transition(HOME, q))

    @unittest.skipUnless(os.getenv("GO1_FULL_SCENE"), "Set GO1_FULL_SCENE for parity")
    def test_slim_model_matches_full_model(self):
        model = mujoco.MjModel.from_xml_path(os.environ["GO1_FULL_SCENE"])
        data = mujoco.MjData(model)
        self.assertEqual(model.ngeom, self.checker.model.ngeom)
        data.qpos[:7] = [0, 0, 1, 1, 0, 0, 0]
        rng = np.random.default_rng(122)
        for _ in range(1000):
            q = rng.uniform(LOWER, UPPER)
            data.qpos[7:] = q
            mujoco.mj_forward(model, data)
            contacts = [c for c in data.contact[:data.ncon]
                        if tuple(sorted((int(c.geom1), int(c.geom2)))) in self.checker.pairs
                        and c.dist < -0.0009]
            self.assertEqual(self.checker.safe(q), not bool(contacts))

    def test_home_transition_timing(self):
        # Informational, not a realtime guarantee: hardware and ROS scheduling differ.
        start = time.perf_counter()
        for _ in range(10):
            self.assertTrue(self.checker.safe_transition(HOME, HOME + 0.05))
        print("mean transition ms:", (time.perf_counter() - start) * 100)


if __name__ == "__main__":
    unittest.main()
