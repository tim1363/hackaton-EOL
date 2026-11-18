"""Optional approximate public-simulator joint dynamics for Playground MJX.

This only adjusts joint parameters; it is not a replacement for testing in the
public simulator. In particular, public servo torque is clipped after adding
velocity feedback, whereas Playground treats the added damping as passive.
"""
import numpy as np
from mujoco_playground._src import mjx_env


def apply_public_joint_dynamics(env):
    # Public Go1 XML passive damping is 1/2/2, armature .01, frictionloss .2.
    # Deployment uses kd=.5; MJX's actuator is position-only, so approximate
    # that derivative term with extra passive damping.
    model = env._mj_model
    model.dof_damping[6:] = np.tile([1.5, 2.5, 2.5], 4)
    model.dof_armature[6:] = 0.01
    model.dof_frictionloss[6:] = 0.2
    env._mjx_model = mjx_env.put_model(model, impl=env._config.impl)
