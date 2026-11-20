#!/usr/bin/env python3
"""Check received /lowcmd trace against full-model MuJoCo judge-grid samples.

Usage: python check_full_trace.py TRACE.json /path/to/full/scene.xml
The trace format is produced by T3/evaluate_public_sim.py (GO1_EVAL_TRACE).
This checks received samples, not unobserved messages or every possible input.
"""
import csv
import json
import math
from pathlib import Path
import sys

import mujoco
import numpy as np

from safety_core import LOWER, UPPER


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[1]) as source:
        commands = [np.asarray(row[2], dtype=np.float64)
                    for row in json.load(source) if row[1] == 'safe']
    if not commands:
        raise SystemExit('Trace contains no safe commands')
    with (Path(__file__).parent / 'model' / 't2_collision_pairs.csv').open(newline='') as source:
        pairs = {(int(r['geom1_id']), int(r['geom2_id'])) for r in csv.DictReader(source)
                 if r['diagnostic_policy'] == 'checked'}
    model = mujoco.MjModel.from_xml_path(sys.argv[2])
    if model.ngeom != 56 or len(pairs) != 655:
        raise ValueError('Unexpected model or pair list')
    data = mujoco.MjData(model)
    data.qpos[:7] = [0, 0, 1, 1, 0, 0, 0]
    calls, transitions, max_step = 0, 0, 0.0
    previous = None
    for index, target in enumerate(commands):
        if target.shape != (12,) or not np.all(np.isfinite(target)):
            raise ValueError(f'Nonfinite or invalid target at sample {index}')
        if np.any(target < LOWER) or np.any(target > UPPER):
            raise ValueError(f'Joint limit violation at sample {index}')
        start = target if previous is None else previous
        distance = float(np.max(np.abs(target - start)))
        max_step = max(max_step, distance)
        if distance > math.radians(5):
            raise ValueError(f'Target jump {distance} rad at received sample {index}')
        if previous is not None and distance == 0:
            continue
        transitions += int(previous is not None)
        n = max(1, math.ceil(distance / math.radians(0.1)))
        for i in range(n + 1):
            data.qpos[7:] = start + (target - start) * (i / n)
            mujoco.mj_forward(model, data)
            calls += 1
            for j in range(data.ncon):
                contact = data.contact[j]
                pair = tuple(sorted((int(contact.geom1), int(contact.geom2))))
                if pair in pairs and contact.dist < -0.001:
                    raise ValueError(f'Collision at sample {index} grid {i}/{n}: '
                                     f'pair={pair} depth={-contact.dist}')
        previous = target
    print(f'PASS: {len(commands)} received commands, {transitions} changed transitions, '
          f'{calls} full-model configurations, max step {max_step:.9f} rad, '
          f'MuJoCo {mujoco.__version__}')


if __name__ == '__main__':
    main()
