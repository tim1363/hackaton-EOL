"""Evaluate a PPO checkpoint in Playground, not in the official simulator.

This runs independent vectorized episodes with fixed forward commands. Ground
truth is used only for measurement. The T2 collision/ROS block is not applied,
so results do not establish judge success. See README.md for limitations.
"""

import argparse
import json
import time

from brax.training.acme import running_statistics
from brax.training.agents.ppo import checkpoint, networks
import jax
import jax.numpy as jnp
import numpy as np
from mujoco_playground._src.locomotion.go1 import joystick

from safe_joystick import SafeJoystick


class FixedSpeedJoystick(SafeJoystick):
    def sample_command(self, rng, previous):
        del rng, previous
        return jnp.array([self.speed, 0.0, 0.0])


def attitude(q):
    """Convert MuJoCo's body-to-world quaternion (w,x,y,z) to roll/pitch/yaw."""
    w, x, y, z = (q[..., i] for i in range(4))
    roll = jnp.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = jnp.arcsin(jnp.clip(2 * (w * y - z * x), -1, 1))
    yaw = jnp.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return roll, pitch, yaw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", help="Path to one numeric PPO checkpoint directory")
    parser.add_argument("--speed", type=float, default=0.4)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True, help="JSON results path")
    args = parser.parse_args()
    if not 0.1 <= args.speed <= 0.6 or args.episodes < 1:
        parser.error("speed must be in [0.1, 0.6] and episodes must be positive")

    env = FixedSpeedJoystick(config=joystick.default_config(), config_overrides={"impl": "jax"})
    env.speed = args.speed
    dt = float(env.dt)
    if abs(dt - 0.02) > 1e-9:
        raise ValueError(f"Unexpected control timestep: {dt}")
    params = checkpoint.load(args.checkpoint)
    ppo = networks.make_ppo_networks(
        {"state": 45, "privileged_state": 123}, 12,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=(512, 256, 128),
        value_hidden_layer_sizes=(512, 256, 128),
        policy_obs_key="state", value_obs_key="privileged_state",
    )
    policy = networks.make_inference_fn(ppo)(params, deterministic=True)
    batch_reset = jax.vmap(env.reset)
    batch_step = jax.vmap(env.step)
    batch_policy = jax.vmap(policy)
    keys = jax.random.split(jax.random.PRNGKey(args.seed), args.episodes)

    def advance(state):
        actions, _ = batch_policy(state.obs, keys)
        return batch_step(state, actions)

    @jax.jit
    def run():
        state = batch_reset(keys)
        # Warmup allows settling but the same commanded speed is applied.
        state, _ = jax.lax.scan(lambda s, _: (advance(s), None), state, None, length=75)
        start = state.data.qpos[:, :2]
        _, _, yaw = attitude(state.data.qpos[:, 3:7])
        direction = jnp.stack((jnp.cos(yaw), jnp.sin(yaw)), axis=-1)
        false = jnp.zeros(args.episodes, dtype=bool)
        zeros = jnp.zeros(args.episodes, dtype=jnp.int32)
        # Track max progress and first success/fall step. Finished episodes are
        # still simulated in the batch, but their recorded result is frozen.
        initial = (state, jnp.int32(0), false, false, zeros, zeros, zeros,
                   jnp.zeros(args.episodes), jnp.zeros(args.episodes))

        def condition(carry):
            _, step, success, fallen, *_ = carry
            return (step < 4500) & ~jnp.all(success | fallen)

        def body(carry):
            state, step, success, fallen, streak, success_step, fall_step, maximum, final = carry
            state = advance(state)
            step += 1
            active = ~(success | fallen)
            roll, pitch, _ = attitude(state.data.qpos[:, 3:7])
            bad = ((state.data.qpos[:, 2] < 0.16) | (jnp.abs(roll) > jnp.deg2rad(50.0))
                   | (jnp.abs(pitch) > jnp.deg2rad(50.0)))
            bad |= ~jnp.all(jnp.isfinite(state.data.qpos), axis=-1)
            streak = jnp.where(active & bad, streak + 1, jnp.where(active, 0, streak))
            new_fall = active & (streak > 25)
            progress = jnp.sum((state.data.qpos[:, :2] - start) * direction, axis=-1)
            new_success = active & ~new_fall & (progress >= 3.0)
            maximum = jnp.where(active, jnp.maximum(maximum, progress), maximum)
            final = jnp.where(active, progress, final)
            success_step = jnp.where(new_success, step, success_step)
            fall_step = jnp.where(new_fall, step, fall_step)
            return (state, step, success | new_success, fallen | new_fall,
                    streak, success_step, fall_step, maximum, final)

        return jax.lax.while_loop(condition, body, initial)[1:]

    start_wall = time.monotonic()
    step, success, fallen, _, success_step, fall_step, maximum, final = jax.device_get(run())
    result = {
        "scope": "Playground MJX only; no ROS, no T2 collision check, not judge results",
        "checkpoint": args.checkpoint, "seed": args.seed, "speed_mps": args.speed,
        "episode_count": args.episodes, "warmup_seconds": 1.5,
        "max_scored_seconds": 90.0, "control_dt": dt,
        "reference": "heading and position at end of warmup; falls checked after warmup",
        "success_count": int(np.sum(success)), "fall_count": int(np.sum(fallen)),
        "simulated_scored_seconds": float(step * dt), "wall_seconds": time.monotonic() - start_wall,
        "episodes": [
            {"index": i, "success": bool(success[i]), "fell": bool(fallen[i]),
             "time_to_success_s": float(success_step[i] * dt) if success[i] else None,
             "time_to_fall_s": float(fall_step[i] * dt) if fallen[i] else None,
             "max_forward_m": float(maximum[i]), "final_forward_m": float(final[i])}
            for i in range(args.episodes)
        ],
    }
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
