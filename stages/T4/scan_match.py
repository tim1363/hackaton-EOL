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
    left = previous - np.roll(previous, 1, axis=0)
    right = np.roll(previous, -1, axis=0) - previous
    left_length = np.linalg.norm(left, axis=1)
    right_length = np.linalg.norm(right, axis=1)
    tangent = left + right
    tangent_length = np.linalg.norm(tangent, axis=1)
    normals = np.column_stack((-tangent[:, 1], tangent[:, 0])) / np.maximum(tangent_length[:, None], 1e-6)
    aligned = np.sum(left * right, axis=1) >= 0.65 * left_length * right_length
    surface = aligned & (left_length < 0.65) & (right_length < 0.65) & (tangent_length > 1e-3)
    for _ in range(8):
        moved = rotated + offset
        distances = np.sum((moved[:, None, :] - previous[None, :, :])**2, axis=2)
        nearest = np.argmin(distances, axis=1)
        best = distances[np.arange(len(moved)), nearest]
        mask = best < 0.35**2
        if mask.sum() < 20:
            return None
        residual = previous[nearest[mask]] - moved[mask]
        usable = surface[nearest[mask]]
        if usable.sum() >= 18:
            basis = normals[nearest[mask][usable]]
            signed = np.sum(residual[usable] * basis, axis=1)
            scale = max(0.012, 2.5 * np.median(np.abs(signed)))
            weights = np.minimum(1.0, scale / np.maximum(np.abs(signed), 1e-9))
            gram = (basis.T * weights) @ basis
            if np.linalg.eigvalsh(gram)[0] >= 0.05 * np.trace(gram):
                update = np.linalg.solve(gram, basis.T @ (weights * signed))
            else:
                update = np.median(residual, axis=0)
        else:
            update = np.median(residual, axis=0)
        offset += update
        if np.linalg.norm(update) < 1e-4:
            break
    return offset
