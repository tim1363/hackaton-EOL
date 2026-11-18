"""Small planar scan-matching primitives for the experimental T4 node."""
import math

import numpy as np


def quaternion_matrix(q):
    """Unit quaternion (x, y, z, w) to rotation matrix."""
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q)
    if not np.isfinite(norm) or norm < 1e-9:
        raise ValueError("Invalid quaternion")
    x, y, z, w = q / norm
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)],
    ])


def quaternion_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw*bx + ax*bw + ay*bz - az*by,
                     aw*by - ax*bz + ay*bw + az*bx,
                     aw*bz + ax*by - ay*bx + az*bw,
                     aw*bw - ax*bx - ay*by - az*bz])


def yaw_of(q):
    r = quaternion_matrix(q)
    return math.atan2(r[1, 0], r[0, 0])


def yaw_quaternion(yaw):
    return np.array([0., 0., math.sin(yaw/2), math.cos(yaw/2)])


def rotation2(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s], [s, c]])


def match_translation(previous, current, yaw_delta, initial=None):
    """Estimate current trunk translation in previous trunk coordinates.

    Relative yaw comes from IMU; nearest-neighbour ICP estimates translation.
    Returns None when too few nearby correspondences exist. Both point clouds
    must be gravity-levelled and expressed relative to the trunk origin.
    """
    if len(previous) < 20 or len(current) < 20:
        return None
    rotated = current @ rotation2(yaw_delta).T
    offset = np.zeros(2) if initial is None else np.asarray(initial, dtype=float).copy()
    for _ in range(12):
        moved = rotated + offset
        distances = np.sum((moved[:, None, :] - previous[None, :, :])**2, axis=2)
        nearest = np.argmin(distances, axis=1)
        best = distances[np.arange(len(moved)), nearest]
        mask = best < 0.35**2
        if mask.sum() < 20:
            return None
        residual = previous[nearest[mask]] - moved[mask]
        update = np.median(residual, axis=0)
        offset += update
        if np.linalg.norm(update) < 1e-4:
            break
    return offset
