"""ROS 2 wrapper for the T2 target safety filter."""

import copy
import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from unitree_go.msg import LowCmd, LowState

from safety_core import CollisionChecker, HOME, TargetFilter

MOTOR_FIELDS = ("q", "dq", "tau", "kp", "kd")


def valid_command(message):
    # A single invalid floating-point control field invalidates the entire
    # message, including the eight unused MotorCmd entries.
    return all(math.isfinite(getattr(motor, field))
               for motor in message.motor_cmd for field in MOTOR_FIELDS)


def initial_hold():
    msg = LowCmd()
    for i, motor in enumerate(msg.motor_cmd[:12]):
        motor.mode = 0x0A
        motor.q = float(HOME[i])
        motor.dq = 0.0
        motor.tau = 0.0
        motor.kp = 35.0
        motor.kd = 0.5
    return msg


class SafetyNode(Node):
    def __init__(self):
        super().__init__("go1_safety_block", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)
        ])
        self.target_filter = TargetFilter(CollisionChecker())
        self.safe_command = initial_hold()
        self.pending = None
        self.last_valid_input_ns = None
        self.publisher = self.create_publisher(LowCmd, "/lowcmd", 10)
        self.create_subscription(LowCmd, "/lowcmd_bare", self.on_command, 10)
        # Subscribe to the contract's telemetry; initial safe target is the
        # checked home pose, not an unchecked measured configuration.
        self.create_subscription(LowState, "/lowstate", self.on_state, 10)
        # Publish at 100 Hz in simulation time; at most one new command is
        # processed per publication so the emitted stream obeys the step cap.
        self.create_timer(0.01, self.tick)

    def on_state(self, _message):
        pass

    def on_command(self, message):
        # Keep only the newest request; it will be checked on the next tick.
        self.pending = message

    def tick(self):
        now = self.get_clock().now().nanoseconds
        message, self.pending = self.pending, None
        if message is not None and valid_command(message):
            target, accepted = self.target_filter.apply(
                [m.q for m in message.motor_cmd[:12]]
            )
            if accepted:
                self.safe_command = copy.deepcopy(message)
                for i, motor in enumerate(self.safe_command.motor_cmd[:12]):
                    motor.q = float(target[i])
                    # Conservative finite PD/feed-forward bounds. They do not
                    # alter normal Go1 PPO gains (35, 0.5, dq=tau=0).
                    motor.kp = min(max(motor.kp, 0.0), 100.0)
                    motor.kd = min(max(motor.kd, 0.0), 10.0)
                    motor.dq = min(max(motor.dq, -30.0), 30.0)
                    torque_limit = 35.55 if i % 3 == 2 else 23.7
                    motor.tau = min(max(motor.tau, -torque_limit), torque_limit)
                self.last_valid_input_ns = now
        if self.last_valid_input_ns is None or now - self.last_valid_input_ns >= 450_000_000:
            for motor in self.safe_command.motor_cmd[:12]:
                motor.mode = 0x0A
                motor.dq = 0.0
                motor.tau = 0.0
        self.publisher.publish(self.safe_command)


def main():
    rclpy.init()
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
