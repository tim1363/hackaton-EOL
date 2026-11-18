"""Export a Brax PPO actor and verify NumPy inference against Brax.

Run in the pinned training environment; output is a portable, pickle-free NPZ.
"""
import argparse
from pathlib import Path

from brax.training.acme import running_statistics
from brax.training.agents.ppo import checkpoint, networks
import jax
import jax.numpy as jnp
import numpy as np

from numpy_policy import NumpyPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("output")
    args = parser.parse_args()
    params = checkpoint.load(args.checkpoint)
    normalizer, actor = params[0], params[1]["params"]
    payload = {"mean": np.asarray(normalizer.mean["state"]),
               "std": np.asarray(normalizer.std["state"])}
    for i in range(4):
        layer = actor[f"hidden_{i}"]
        payload[f"w{i}"] = np.asarray(layer["kernel"])
        payload[f"b{i}"] = np.asarray(layer["bias"])
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)

    ppo = networks.make_ppo_networks(
        {"state": 45, "privileged_state": 123}, 12,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=(512, 256, 128),
        value_hidden_layer_sizes=(512, 256, 128),
        policy_obs_key="state", value_obs_key="privileged_state")
    policy = networks.make_inference_fn(ppo)(params, deterministic=True)
    rng = np.random.default_rng(42)
    # Sample in normalized coordinates so comparisons cover the actor's input range.
    x = payload["mean"] + rng.normal(size=(128, 45)).astype(np.float32) * payload["std"]
    keys = jax.random.split(jax.random.PRNGKey(0), len(x))
    expected, _ = jax.vmap(policy)({"state": jnp.asarray(x)}, keys)
    actual = NumpyPolicy(path)(x)
    error = float(np.max(np.abs(actual - np.asarray(expected))))
    if error > 1e-5:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"Brax/NumPy parity failed: max error {error}")
    print(f"Exported {path}; 128-sample max absolute action error: {error:.3g}")


if __name__ == "__main__":
    main()
