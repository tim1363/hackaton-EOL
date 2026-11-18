# Go1 PPO training adapter

`safe_joystick.py` adapts the pinned Playground Go1 joystick task for Brax PPO.
The actor receives gyro, body-frame gravity, joint positions and velocities,
the last filtered target (as an action offset), and commanded velocity; it does
**not** receive simulator-only linear velocity. The critic retains privileged
training observations. Commands are sampled forward in the judge's 0.1–0.6 m/s
range. The normal Go1 PPO reward and network configuration are inherited from
Playground.

At each 20 ms control step, the adapter rejects non-finite action vectors,
clamps joint targets to the T2 joint limits, and limits each target's change to
5 degrees from the last accepted target, matching the T2 position/step filter.
An experimental `EXACT_T2_COLLISION=1` CPU callback also runs the T2 path
checker, including all 655 pairs and intermediate samples, for every target.
Its CPU batching/parity smoke test passed, but PPO training with the callback
has not been run. It is expected to be much slower than GPU-only training. The initial `ppo-v3` run does not
use the callback. The callback uses the training environment's MuJoCo version;
the judge uses MuJoCo 3.3.7, so parity is not guaranteed. ROS transport,
timing jitter and the watchdog are not emulated. End-to-end validation through
the experimental ROS block has now been exercised in the public simulator; its
full T2 requirements still need independent validation.

## Run status (18 November 2026)

The `ppo-v3` training loop finished 104,857,600 environment steps despite the
requested 80,000,000; its last logged evaluation reward was 33.354. This is not
a judge success metric. Checkpoints, environment configuration, package
versions, TensorBoard data, and `console.log` are on the T4 host in
`/kaggle/working/rh-runs/ppo-v3/`, not checked into Git. The run is also tracked
[in W&B](https://forge.coreweave.com/wandb/wandb-abreow-abreow/unitree/runs/0kyqsy03).
A separate Playground MJX evaluation of checkpoint `000104857600` at 0.4 m/s,
seed 42, reached 3 m in 10/10 episodes (8.28–9.02 s after 1.5 s warmup),
without detected falls. It used the run's original adapter snapshot with joint
and step limits, but no collision checking or ROS. This is not a Judge result.
The JSON is in `/opt/data/rh/ppo-v3/eval-0.4-seed42.json` and on the T4 host.
Run `evaluate_playground.py` with the exact `source/safe_joystick.py` snapshot
from that run, not necessarily the current repository adapter.

The ten-trial source snapshot is preserved under
`/opt/data/rh/public-test/trial-source/`.

## Public simulator trial (18 November 2026)

Using released `registry.cookcloud.ru/go1-hackathon-remote-stage/go1-sim:v1.0`
(digest `sha256:c79ddbece6cc7d00f114a9a9a09be0bae061ebb35ca722bcbe51bf75fce1b2e3`),
we recreated the container and simulator for each of ten episodes. At 0.4 m/s,
9/10 reached 3 m without a detected fall, in 22.22–24.32 s after 1.5 s warmup;
one fell at 2.24 m after 17.52 s. All used the same nominal simulator initial
pose; this is not the private Judge. The maximum observed `/lowcmd` gap was
32–34 ms; this is not a complete timing or watchdog proof. The separate ground
truth evaluator alone reads `/odom/ground_truth`; the controller does not.
Raw logs and the exact trial source snapshot are in `/opt/data/rh/public-test/`.

In an additional instrumented episode, T2 modified all of the first 1,200 raw
requests and rejected none of those checks; the largest observed safe target
step was 0.08726454 rad (<5°). Offline rechecking of all 1,855 observed safe
outputs with the same T2 core found no limit, step or sampled-transition
violations (`check_safety_trace.py`); this is not an independent Judge check or
complete collision coverage.
The released simulator has higher joint damping and armature than the training
model; the effect on gait and the single fall remain to be investigated.

For one isolated rootless Podman trial after loading the released image and
exporting the actor (replace `IMAGE` and `ACTOR` as needed):

```bash
IMAGE=localhost/v1.0:latest
ACTOR=/opt/data/rh/ppo-v3/actor-104857600.npz
tmp=$(mktemp -d); mkdir "$tmp/rh"
cp -a stages/T2 stages/T3 "$tmp/rh/"
cp "$ACTOR" "$tmp/rh/actor.npz"
c=$(podman create --entrypoint /bin/bash "$IMAGE" /tmp/rh/T3/run_public_sim.sh)
podman cp "$tmp/rh" "$c":/tmp/rh
podman start -a "$c"
podman rm "$c"; rm -rf "$tmp"
```

No host networking, host IPC, GPU, host device, extra capability, privileged
mode or bind mount is required. The evaluator is deliberately informal and
measures projected displacement/falls from debug ground truth only for scoring.
Set `GO1_SAFETY_TRACE=1` and `GO1_EVAL_TRACE=/tmp/eval-trace.json` at container
creation for optional diagnostic counters and a ROS observation trace.


## Reproduce on prepared T4 host

- Playground revision: `3ff05b53d303f92b30a457c2973036186f2ffe13`, under
  `/kaggle/working/rh-references/mujoco_playground/rss2025`.
- Allow Playground to populate its pinned Menagerie assets via
  `mujoco_playground._src.mjx_env.ensure_menagerie_exists()`.
- Install the Playground JAX/MJX/Brax training dependencies in `.venv`.
  The working T4 setup uses JAX and jaxlib `0.7.2`, MuJoCo `3.16.0`,
  Brax `0.14.2`. JAX `0.12.0.1` fails because Brax still calls the removed
  `jax.device_put_replicated` API.
- `LD_LIBRARY_PATH=/usr/local/nvidia/lib64`, unset `PYTHONPATH`, and set
  `PYTHONNOUSERSITE=1` to select the working GPU libraries on this host.
- Run `python smoke_test.py` inside that environment; it requires a GPU.
- Copy this directory to the host, then run
  `RUN_DIR=/kaggle/working/rh-runs/<new-name> bash launch.sh > <log> 2>&1`.
  `launch.sh` copies the exact source into the run, records revisions/package
  versions, and saves configs, checkpoints and TensorBoard logs. Set
  `NUM_TIMESTEPS`, `NUM_ENVS`, `NUM_EVALS`, or `SEED` for overrides.
  W&B goes to `wandb-abreow-abreow/unitree`; the launch script reads the
  existing key from `/kaggle/working/.secrets/wandb_api_key` without logging it.
- For collision-aware fine-tuning, set `EXACT_T2_COLLISION=1`,
  `SAFETY_CORE_DIR` to the directory containing `safety_core.py` and `model/`,
  and `LOAD_CHECKPOINT_PATH` to the parent `checkpoints/` directory. Reduce `NUM_ENVS`
  because collision checks are serialized on the CPU. The exact T2 source and
  model are copied into the run directory for provenance.
- Keep the entire run directory and console log as training provenance.

The actor observation ordering and filtered-target update must be reproduced
exactly in the deployed ROS node; Playground's upstream observation normally
lags the action by an extra step, which this adapter intentionally corrects.

`export_policy.py CHECKPOINT OUTPUT.npz` exports a portable actor and compares
128 deterministic actions against Brax. For checkpoint `000104857600`, maximum
absolute error was `6.11e-7`; the exported file is stored at
`/opt/data/rh/ppo-v3/actor-104857600.npz` (SHA-256
`7a0e0d2f83017c881e2590079c01b7b6dd7ccd27d66d7e522a81d61c1ce9e0cd`).

