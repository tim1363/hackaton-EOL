import argparse
from pathlib import Path

import numpy as np


class Actor:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as weights:
            self.layers = [
                (weights[f"weight_{index}"], weights[f"bias_{index}"])
                for index in range(3)
            ]

    def predict(self, observations):
        output = np.asarray(observations, dtype=np.float32)
        for index, (weight, bias) in enumerate(self.layers):
            output = output @ weight.T + bias
            if index < len(self.layers) - 1:
                output = np.tanh(output)
        return np.clip(output, -1.0, 1.0)


def main():
    parser = argparse.ArgumentParser(description="Verify exported Go1 inference using only NumPy.")
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    with np.load(args.run / "parity.npz", allow_pickle=False) as fixture:
        actual = Actor(args.run / "actor.npz").predict(fixture["observations"])
        expected = fixture["actions"]
        np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-6)
        print(f"Inference parity OK: {len(actual)} observations, max error {np.max(np.abs(actual - expected)):.2e}")


if __name__ == "__main__":
    main()
