"""Recheck an evaluation ROS trace using the same T2 core, not the Judge."""
import argparse
import json
import math

import numpy as np
from safety_core import CollisionChecker, LOWER, UPPER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    args = parser.parse_args()
    with open(args.trace) as source:
        rows = [np.asarray(row[2], dtype=float) for row in json.load(source) if row[1] == "safe"]
    if not rows:
        raise ValueError("No /lowcmd samples in trace")
    checker = CollisionChecker()
    violations, max_step = 0, 0.0
    previous = None
    for q in rows:
        if q.shape != (12,) or not np.all(np.isfinite(q)):
            raise ValueError("Invalid target vector in trace")
        violations += bool(np.any(q < LOWER) or np.any(q > UPPER))
        if previous is None:
            violations += not checker.safe(q)
        else:
            step = float(np.max(np.abs(q - previous)))
            max_step = max(max_step, step)
            violations += step > math.radians(5) + 1e-8
            if step > 1e-9:
                violations += not checker.safe_transition(previous, q)
        previous = q
    print(f"{len(rows)} samples; max step {max_step:.9f} rad; violations {violations}")
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
