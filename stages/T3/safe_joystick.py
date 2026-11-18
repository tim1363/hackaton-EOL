"""Go1 PPO environment with deployable actor inputs and a target safety filter.

Requires the pinned mujoco_playground checkout documented in README.md.
The optional CPU callback invokes the production T2 collision checker.
"""

import os


import jax
import jax.numpy as jnp

from mujoco_playground._src.locomotion.go1 import joystick


if os.environ.get("EXACT_T2_COLLISION") == "1":
    from collision_callback import collision_filter
else:
    collision_filter = None

# T2 limits, ordered FR, FL, RR, RL (hip, thigh, calf).
JOINT_LOWER = jnp.tile(jnp.array([-0.863, -0.686, -2.818]), 4) + 0.000001
JOINT_UPPER = jnp.tile(jnp.array([0.863, 4.501, -0.888]), 4) - 0.000001
MAX_TARGET_STEP = 5.0 * jnp.pi / 180.0 - 0.000002


def filter_targets(previous, requested):
    """Clamp target and per-tick change; reject the whole non-finite vector."""
    finite = jnp.all(jnp.isfinite(requested))
    # Avoid NaNs entering intermediate computations on accelerators.
    requested = jnp.where(finite, requested, previous)
    target = jnp.clip(requested, JOINT_LOWER, JOINT_UPPER)
    target = previous + jnp.clip(target - previous, -MAX_TARGET_STEP, MAX_TARGET_STEP)
    target = jnp.where(finite, target, previous)
    if collision_filter is not None:
        target = collision_filter(previous, target)
    return target


class SafeJoystick(joystick.Joystick):
    """Train at 50 Hz with T2 target filtering and optional collision checks.

    ROS transport, timing jitter and the missing-input watchdog are not modeled.
    The production ROS T2 block and judge remain authoritative.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if os.environ.get("PUBLIC_JOINT_DYNAMICS") == "1":
            from joint_dynamics import apply_public_joint_dynamics
            apply_public_joint_dynamics(self)


    def _get_obs(self, data, info):
        obs = super()._get_obs(data, info)
        # Upstream actor state starts with simulator-only body linear velocity.
        # Gyro, projected gravity, joint position/velocity, last action, command
        # are all available or reconstructible from LowState/cmd_vel.
        obs["state"] = obs["state"][3:]
        return obs

    def sample_command(self, rng, _previous):
        # Judge tests forward-only commands in [0.1, 0.6] m/s.
        speed = jax.random.uniform(rng, (), minval=0.1, maxval=0.6)
        return jnp.array([speed, 0.0, 0.0])

    def reset(self, rng):
        state = super().reset(rng)
        state.info["safe_target"] = self._default_pose
        state.info["rng"], key = jax.random.split(state.info["rng"])
        state.info["command"] = self.sample_command(key, state.info["command"])
        return state.replace(obs=self._get_obs(state.data, state.info))

    def step(self, state, action):
        target = filter_targets(
            state.info["safe_target"],
            self._default_pose + action * self._config.action_scale,
        )
        state.info["safe_target"] = target
        filtered_action = (target - self._default_pose) / self._config.action_scale
        state = super().step(state, filtered_action)
        # Upstream builds observations before updating last_act. Expose the
        # target just applied, so the actor can reconstruct the filter state.
        obs = dict(state.obs)
        obs["state"] = obs["state"].at[30:42].set(filtered_action)
        return state.replace(obs=obs)
