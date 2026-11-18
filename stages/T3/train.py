"""Launch upstream Brax PPO with our Go1 environment and W&B project."""

import os

import mujoco_playground
from mujoco_playground._src.locomotion.go1 import joystick

from safe_joystick import SafeJoystick

# Override the existing entry so upstream PPO configuration and domain
# randomization continue to be selected by their standard Go1 name.
mujoco_playground.locomotion.register_environment(
    "Go1JoystickFlatTerrain", SafeJoystick, joystick.default_config
)

from learning import train_jax_ppo  # noqa: E402

if train_jax_ppo.wandb is not None:
    original_init = train_jax_ppo.wandb.init

    def init_wandb(*args, **kwargs):
        kwargs["project"] = os.environ.get("WANDB_PROJECT", "unitree")
        kwargs.setdefault("entity", os.environ.get("WANDB_ENTITY", "wandb-abreow-abreow"))
        return original_init(*args, **kwargs)

    train_jax_ppo.wandb.init = init_wandb

if __name__ == "__main__":
    train_jax_ppo.run()
