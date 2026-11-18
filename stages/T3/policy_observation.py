"""Build the trained Go1 actor's non-privileged observation from ROS values."""
import numpy as np

# Playground's flat-terrain keyframe, in FR, FL, RR, RL motor order.
DEFAULT_POSE = np.array([0.1, 0.9, -1.8, -0.1, 0.9, -1.8,
                         0.1, 0.9, -1.8, -0.1, 0.9, -1.8], dtype=np.float32)
ACTION_SCALE = 0.5


def observation(quaternion, gyro, joint_position, joint_velocity, safe_target, command):
    """Return gyro, projected gravity, joint offsets/velocities, safe action, command.

    Quaternion is body-to-world, (w,x,y,z). Only accepted /lowcmd targets are
    used for the previous action, not private simulator state.
    """
    quat = np.asarray(quaternion, dtype=np.float64)
    gyro = np.asarray(gyro, dtype=np.float32)
    q = np.asarray(joint_position, dtype=np.float32)
    dq = np.asarray(joint_velocity, dtype=np.float32)
    target = np.asarray(safe_target, dtype=np.float32)
    cmd = np.asarray(command, dtype=np.float32)
    if any(x.shape != shape or not np.all(np.isfinite(x)) for x, shape in (
        (quat, (4,)), (gyro, (3,)), (q, (12,)), (dq, (12,)),
        (target, (12,)), (cmd, (3,)))):
        raise ValueError("Invalid policy observation inputs")
    norm = np.linalg.norm(quat)
    if norm < 1e-8:
        raise ValueError("Invalid zero quaternion")
    w, x, y, z = quat / norm
    gravity = np.array([2 * (w*y - x*z), -2 * (y*z + w*x),
                        -1 + 2 * (x*x + y*y)], dtype=np.float32)
    return np.concatenate((gyro, gravity, q - DEFAULT_POSE, dq,
                           (target - DEFAULT_POSE) / ACTION_SCALE, cmd))
