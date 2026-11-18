"""Dependency-light deterministic inference for the trained Brax Go1 actor.

The exported .npz contains only the actor and observation normalizer. This
module does not reconstruct observations or issue motor commands; callers must
reproduce the training adapter and route commands through T2.
"""

from pathlib import Path

import numpy as np


class NumpyPolicy:
    """Brax PPO's normalized 45-input, swish MLP, tanh-mode actor."""

    def __init__(self, path):
        with np.load(Path(path), allow_pickle=False) as data:
            self.mean = np.asarray(data["mean"], dtype=np.float32).copy()
            self.std = np.asarray(data["std"], dtype=np.float32).copy()
            self.weights = [np.asarray(data[f"w{i}"], dtype=np.float32).copy() for i in range(4)]
            self.biases = [np.asarray(data[f"b{i}"], dtype=np.float32).copy() for i in range(4)]
        expected = [(45, 512), (512, 256), (256, 128), (128, 24)]
        if self.mean.shape != (45,) or self.std.shape != (45,):
            raise ValueError("Expected a 45-dimensional observation normalizer")
        if not np.all(np.isfinite(self.mean)) or not np.all(np.isfinite(self.std)) or np.any(self.std <= 0):
            raise ValueError("Invalid observation normalizer")
        for weight, bias, shape in zip(self.weights, self.biases, expected):
            if weight.shape != shape or bias.shape != (shape[1],):
                raise ValueError("Unexpected actor layer shape")
            if not np.all(np.isfinite(weight)) or not np.all(np.isfinite(bias)):
                raise ValueError("Non-finite actor parameters")

    def __call__(self, observations):
        x = np.asarray(observations, dtype=np.float32)
        if x.ndim < 1 or x.shape[-1] != 45 or not np.all(np.isfinite(x)):
            raise ValueError("Expected finite observations with final dimension 45")
        x = (x - self.mean) / self.std
        for weight, bias in zip(self.weights[:-1], self.biases[:-1]):
            x = x @ weight + bias
            # Brax uses swish/silu. Clip only the exponent to prevent overflow.
            x = x / (1.0 + np.exp(-np.clip(x, -80.0, 80.0)))
        logits = x @ self.weights[-1] + self.biases[-1]
        action = np.tanh(logits[..., :12])
        if not np.all(np.isfinite(action)):
            raise ValueError("Non-finite actor output")
        return action
