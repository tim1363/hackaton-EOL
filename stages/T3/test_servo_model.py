"""Check the Playground servo actuator against the public torque equation.

Run in the pinned Playground environment with PUBLIC_JOINT_DYNAMICS=servo.
This verifies actuator forces, not whole-simulator equivalence.
"""
import os

import mujoco
from mujoco import mjx
import jax
import numpy as np
from mujoco_playground._src.locomotion.go1 import joystick

from safe_joystick import SafeJoystick


def main():
    assert os.environ.get("PUBLIC_JOINT_DYNAMICS") == "servo"
    env = SafeJoystick(config=joystick.default_config(), config_overrides={"impl": "jax"})
    model = env.mj_model
    data = mujoco.MjData(model)
    rng = np.random.default_rng(123)
    limits = np.tile([23.7, 23.7, 35.55], 4)
    saturated = 0
    unsaturated = 0
    for _ in range(128):
        # Within the existing actuator control range, as enforced by T2.
        q = rng.uniform(model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        target = rng.uniform(model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        dq = rng.uniform(-50.0, 50.0, size=12)
        data.qpos[7:] = q
        data.qvel[6:] = dq
        data.ctrl[:] = target
        mujoco.mj_forward(model, data)
        unclipped = 35.0 * (target - q) - 0.5 * dq
        expected = np.clip(unclipped, -limits, limits)
        np.testing.assert_allclose(data.actuator_force, expected, atol=1e-10, rtol=1e-10)
        saturated += int(np.count_nonzero(np.abs(unclipped) > limits))
        unsaturated += int(np.count_nonzero(np.abs(unclipped) < limits))
    assert saturated and unsaturated
    # The rollout runs MJX, not native MuJoCo. Check the final sampled state
    # through its forward pass too (float32 GPU arithmetic needs tolerance).
    mjx_data = mjx.put_data(model, data, impl="jax")
    mjx_data = jax.jit(mjx.forward)(env.mjx_model, mjx_data)
    np.testing.assert_allclose(np.asarray(mjx_data.actuator_force), data.actuator_force,
                               atol=1e-4, rtol=1e-5)
    print(f"SERVO_FORCE_PARITY_OK saturated={saturated} unsaturated={unsaturated}")


if __name__ == "__main__":
    main()
