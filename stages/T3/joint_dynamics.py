"""Optional public-simulator joint parameters for Playground MJX.

Neither mode reproduces the entire public simulator. The servo mode clips the
combined PD torque like the public low-level controller for our fixed gains,
zero desired velocity and zero feedforward. Contacts, solver, ROS and timing
still differ.
"""
import numpy as np
from mujoco_playground._src import mjx_env


def apply_public_joint_dynamics(env, *, servo=False):
    # Public XML: passive damping 1/2/2, armature .01, frictionloss .2.
    model = env._mj_model
    if servo:
        # MuJoCo position actuators implement force = kp*(target-q) +
        # biasprm[2]*dq. Existing per-actuator force limits clip the combined
        # expression. Our deployed policy uses kp=35, kd=.5, dq_des=tau_ff=0.
        np.testing.assert_allclose(model.actuator_gear[:, 0], 1.0)
        np.testing.assert_allclose(model.actuator_gainprm[:, 0], 35.0)
        np.testing.assert_allclose(model.actuator_biasprm[:, 1], -35.0)
        np.testing.assert_allclose(model.actuator_biasprm[:, 2], 0.0)
        assert np.all(model.actuator_forcelimited)
        model.actuator_biasprm[:, 2] = -0.5
        model.dof_damping[6:] = np.tile([1.0, 2.0, 2.0], 4)
    else:
        # Historical v4 approximation: derivative feedback as passive damping;
        # unlike the real servo it is not included in the force clipping.
        model.dof_damping[6:] = np.tile([1.5, 2.5, 2.5], 4)
    model.dof_armature[6:] = 0.01
    model.dof_frictionloss[6:] = 0.2
    env._mjx_model = mjx_env.put_model(model, impl=env._config.impl)
