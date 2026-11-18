"""Optional exact T2 collision decision for JAX training via CPU callback.

This is far slower than a GPU-only approximation, but uses the same checker and
transition sampling as the deployed safety core. It is intended for fine-tuning
and parity experiments, not as a claim that MJX has native collision checking.
"""

import os
import sys
import threading

import jax
import numpy as np

sys.path.insert(0, os.environ["SAFETY_CORE_DIR"])
from safety_core import CollisionChecker  # noqa: E402

_checker = CollisionChecker()
_lock = threading.Lock()


def _check(previous, candidate):
    previous = np.asarray(previous)
    candidate = np.asarray(candidate)
    shape = candidate.shape
    before = previous.reshape(-1, 12)
    after = candidate.reshape(-1, 12)
    result = after.copy()
    # JAX may issue callbacks from more than one device/thread. MjData is
    # mutable, so serialize access; preserve per-environment decisions.
    with _lock:
        for i in range(len(after)):
            if not _checker.safe_transition(before[i], after[i]):
                result[i] = before[i]
    return result.reshape(shape)


def collision_filter(previous, candidate):
    return jax.pure_callback(
        _check, jax.ShapeDtypeStruct(candidate.shape, candidate.dtype),
        previous, candidate, vmap_method="legacy_vectorized",
    )
