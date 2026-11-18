"""Smoke test the training adapter against the pinned Playground checkout."""

import numpy as np
import jax
import jax.numpy as jnp

from safe_joystick import JOINT_LOWER, JOINT_UPPER, MAX_TARGET_STEP, SafeJoystick, filter_targets
from mujoco_playground._src.locomotion.go1 import joystick


def main():
    devices = jax.devices()
    assert any(d.platform == "gpu" for d in devices), devices
    previous = jnp.tile(jnp.array([0.0, 0.9, -1.8]), 4)
    limit = float(MAX_TARGET_STEP)
    first = jax.jit(filter_targets)(previous, previous + 1.0)
    np.testing.assert_allclose(np.asarray(first - previous), limit, atol=2e-7)
    bad = previous.at[4].set(jnp.nan)
    np.testing.assert_allclose(filter_targets(previous, bad), previous)
    repeated = previous
    for _ in range(100):
        repeated = filter_targets(repeated, previous + 100.0)
    assert np.all(np.asarray(repeated) <= np.asarray(JOINT_UPPER) + 1e-6)
    assert np.all(np.asarray(repeated) >= np.asarray(JOINT_LOWER) - 1e-6)

    env = SafeJoystick(config=joystick.default_config(), config_overrides={"impl": "jax"})
    state = jax.jit(env.reset)(jax.random.PRNGKey(0))
    assert state.obs["state"].shape == (45,), state.obs["state"].shape
    assert state.obs["privileged_state"].shape[0] > 45
    assert 0.1 <= float(state.info["command"][0]) <= 0.6
    state = jax.jit(env.step)(state, jnp.ones(12))
    assert np.all(np.abs(np.asarray(state.info["safe_target"] - env._default_pose)) <= limit + 2e-7)
    np.testing.assert_allclose(state.data.ctrl, state.info["safe_target"], atol=2e-7)
    print("SMOKE_OK", devices, flush=True)


if __name__ == "__main__":
    main()
