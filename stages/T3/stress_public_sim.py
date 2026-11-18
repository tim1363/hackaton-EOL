#!/usr/bin/env python3
"""Non-Judge robustness experiment for the released MuJoCo simulator.

Perturb initial pose/joints and floor/robot friction, deterministically by seed.
This is simulator-side evaluation only; no ground truth enters the policy.
"""
import json
import os
import sys

import mujoco
import numpy as np
import rclpy

sys.path.insert(0, "/home/ros/go1_ws/src/go1_simulation/scripts")
from go1_mujoco import Go1MuJoCo  # noqa: E402


def main():
    seed = int(os.environ["GO1_STRESS_SEED"])
    rng = np.random.default_rng(seed)
    roll, pitch = rng.uniform(-0.04, 0.04, size=2)
    yaw = rng.uniform(-0.15, 0.15)
    dz = rng.uniform(-0.005, 0.005)
    joint_delta = rng.uniform(-0.04, 0.04, size=12)
    friction_scale = rng.uniform(0.85, 1.15)

    rclpy.init(args=sys.argv)
    node = Go1MuJoCo()
    try:
        # Compose a small roll/pitch/yaw offset with the simulator's home pose.
        dq = np.empty(4)
        mujoco.mju_euler2Quat(dq, np.array([roll, pitch, yaw]), "xyz")
        orientation = np.empty(4)
        mujoco.mju_mulQuat(orientation, node.data.qpos[3:7], dq)
        node.data.qpos[3:7] = orientation
        node.data.qpos[2] += dz
        node.data.qpos[node.u_qadr] += joint_delta
        node.hold_q = np.array([node.data.qpos[a] for a in node.u_qadr])
        node.model.geom_friction[:, 0] *= friction_scale
        mujoco.mj_forward(node.model, node.data)
        print("STRESS_PARAMETERS=" + json.dumps({
            "seed": seed, "roll": roll, "pitch": pitch, "yaw": yaw,
            "height_offset": dz, "joint_delta": joint_delta.tolist(),
            "friction_scale": friction_scale,
        }, sort_keys=True), flush=True)
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
