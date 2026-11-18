"""Experimental ROS 2 actor: /lowstate + /cmd_vel -> /lowcmd_bare via T2."""
import os

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from unitree_go.msg import LowCmd, LowState

from numpy_policy import NumpyPolicy
from policy_observation import ACTION_SCALE, DEFAULT_POSE, observation


class PolicyNode(Node):
    def __init__(self):
        super().__init__("go1_rl_policy", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.policy = NumpyPolicy(os.environ["GO1_POLICY_NPZ"])
        self.state = None
        self.command = None
        # Match T2's initial hold until an actual accepted output is observed.
        self.safe_target = np.tile([0.0, 0.9, -1.8], 4)
        self.publisher = self.create_publisher(LowCmd, "/lowcmd_bare", 10)
        self.create_subscription(LowState, "/lowstate", self.on_state, 10)
        self.create_subscription(Twist, "/cmd_vel", self.on_command, 10)
        self.create_subscription(LowCmd, "/lowcmd", self.on_safe_command, 10)
        self.create_timer(0.02, self.tick)

    def on_state(self, msg):
        self.state = msg

    def on_command(self, msg):
        cmd = np.array([msg.linear.x, msg.linear.y, msg.angular.z])
        if np.all(np.isfinite(cmd)):
            self.command = cmd

    def on_safe_command(self, msg):
        target = np.array([m.q for m in msg.motor_cmd[:12]])
        if np.all(np.isfinite(target)):
            self.safe_target = target

    def tick(self):
        if self.state is None or self.command is None:
            return
        try:
            inputs = observation(
                self.state.imu_state.quaternion, self.state.imu_state.gyroscope,
                [m.q for m in self.state.motor_state[:12]],
                [m.dq for m in self.state.motor_state[:12]],
                self.safe_target, self.command)
            target = DEFAULT_POSE + ACTION_SCALE * self.policy(inputs)
        except ValueError as exc:
            self.get_logger().warning(f"Invalid observation; not publishing: {exc}")
            return
        msg = LowCmd()
        for i, motor in enumerate(msg.motor_cmd[:12]):
            motor.mode = 0x0A
            motor.q = float(target[i])
            motor.dq = 0.0
            motor.tau = 0.0
            motor.kp = 35.0
            motor.kd = 0.5
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
