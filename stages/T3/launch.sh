#!/usr/bin/env bash
# Run from any directory on the prepared T4 machine. Set RUN_DIR for each run.
set -euo pipefail
: "${RUN_DIR:?Set RUN_DIR to a new persistent directory}"
PLAYGROUND=${PLAYGROUND:-/kaggle/working/rh-references/mujoco_playground/rss2025}
SECRET=${WANDB_KEY_FILE:-/kaggle/working/.secrets/wandb_api_key}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$RUN_DIR/source" "$RUN_DIR/logs"
RUN_DIR=$(cd "$RUN_DIR" && pwd)
cp "$HERE"/{train.py,safe_joystick.py,smoke_test.py,launch.sh} "$RUN_DIR/source/"
cd "$PLAYGROUND"
git rev-parse HEAD > "$RUN_DIR/playground-revision.txt"
git -C mujoco_playground/external_deps/mujoco_menagerie rev-parse HEAD > "$RUN_DIR/menagerie-revision.txt"
uv pip freeze --python .venv/bin/python > "$RUN_DIR/python-packages.txt"
export PYTHONNOUSERSITE=1 LD_LIBRARY_PATH=/usr/local/nvidia/lib64
unset PYTHONPATH
export WANDB_API_KEY="$(< "$SECRET")"
export WANDB_PROJECT=unitree WANDB_ENTITY=wandb-abreow-abreow
export WANDB_DIR="$RUN_DIR"
export PYTHONUNBUFFERED=1
export MUJOCO_GL=egl
# 50 Hz control; 4096 parallel envs across both T4s. Checkpoints/evaluation
# roughly every 5M transitions, with all effective hyperparameters in stdout.
exec .venv/bin/python -u "$RUN_DIR/source/train.py" \
  --env_name=Go1JoystickFlatTerrain --impl=jax \
  --num_timesteps="${NUM_TIMESTEPS:-80000000}" --num_envs="${NUM_ENVS:-4096}" \
  --num_evals="${NUM_EVALS:-17}" --num_eval_envs=32 \
  --use_wandb --use_tb \
  --logdir="$RUN_DIR/logs" --suffix=safe-ppo --seed="${SEED:-1}"
