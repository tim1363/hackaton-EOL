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
5 degrees from the last accepted target. These are the *position/step* parts
of T2; collision checking, transport, timing jitter and the watchdog are not yet
emulated. This approximation does not establish T2 or T3 compliance. Policy
training must be followed by validation and, if needed, fine-tuning against
actual T2 decisions, including collision checks, in the public simulator.

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
- Keep the entire run directory and console log as training provenance.

The actor observation ordering and filtered-target update must be reproduced
exactly in the deployed ROS node; Playground's upstream observation normally
lags the action by an extra step, which this adapter intentionally corrects.
