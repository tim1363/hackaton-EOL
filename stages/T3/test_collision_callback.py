"""CPU test for callback batching and parity with the production T2 checker."""
import jax
import jax.numpy as jnp
import numpy as np

from collision_callback import _checker, collision_filter
from safety_core import HOME, LOWER, UPPER


def main():
    rng = np.random.default_rng(47)
    for _ in range(1000):
        colliding = rng.uniform(LOWER, UPPER)
        if not _checker.safe(colliding):
            break
    else:
        raise AssertionError("failed to find colliding example")
    previous = np.tile(HOME.astype(np.float32), (2, 1))
    targets = np.stack([HOME + 0.01, colliding]).astype(np.float32)
    result = jax.jit(jax.vmap(collision_filter))(jnp.asarray(previous), jnp.asarray(targets))
    np.testing.assert_allclose(result[0], targets[0], atol=1e-6)
    np.testing.assert_allclose(result[1], previous[1], atol=1e-6)
    devices = jax.local_device_count()
    distributed = jax.pmap(jax.vmap(collision_filter))(
        jnp.broadcast_to(jnp.asarray(previous), (devices, 2, 12)),
        jnp.broadcast_to(jnp.asarray(targets), (devices, 2, 12)),
    )
    np.testing.assert_allclose(distributed[:, 0, :],
                               np.tile(targets[0], (devices, 1)), atol=1e-6)
    np.testing.assert_allclose(distributed[:, 1, :],
                               np.tile(previous[1], (devices, 1)), atol=1e-6)
    print("CALLBACK_PARITY_OK", result.shape, "devices:", devices)


if __name__ == "__main__":
    main()
