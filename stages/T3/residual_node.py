import os

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from unitree_go.msg import LowCmd, LowState

from residual_policy import ResidualPolicy


class PolicyNode(Node):
    def __init__(self):
        super().__init__("go1_t3_controller", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.policy = ResidualPolicy(os.environ["GO1_POLICY_DIR"])
        self.state = None
        self.state_ns = None
        self.speed = 0.0
        self.publisher = self.create_publisher(LowCmd, "/lowcmd_bare", 10)
        self.create_subscription(LowState, "/lowstate", self.receive_state, qos_profile_sensor_data)
        self.create_subscription(Twist, "/cmd_vel", self.receive_speed, 10)
        self.create_timer(1 / self.policy.rate, self.step)

    def receive_state(self, message):
        self.state = message
        self.state_ns = self.get_clock().now().nanoseconds

    def receive_speed(self, message):
        if np.isfinite(message.linear.x):
            self.speed = float(np.clip(message.linear.x, 0.0, 0.6))

    def step(self):
        if self.state is None or self.get_clock().now().nanoseconds - self.state_ns > 250_000_000:
            return
        sensors = self.state
        try:
            target = self.policy.target(
                sensors.imu_state.quaternion, sensors.imu_state.gyroscope,
                [joint.q for joint in sensors.motor_state[:12]],
                [joint.dq for joint in sensors.motor_state[:12]], self.speed)
        except ValueError:
            return
        output = LowCmd()
        for motor, goal in zip(output.motor_cmd[:12], target):
            motor.mode = 0x0A
            motor.q = float(goal)
            motor.kp = self.policy.kp
            motor.kd = self.policy.kd
        self.publisher.publish(output)


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
