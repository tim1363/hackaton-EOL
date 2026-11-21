"""Drive a public Gazebo square; ground truth is consumed only by this test."""
import json
import math
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from std_msgs.msg import Bool
from tf2_msgs.msg import TFMessage

from scan_match import rotation2, yaw_of


def read_pose(position, orientation):
    quat = np.array([orientation.x, orientation.y, orientation.z, orientation.w])
    assert abs(np.linalg.norm(quat) - 1.0) < 1e-4
    pose = np.array([position.x, position.y, position.z, yaw_of(quat)])
    assert np.all(np.isfinite(pose))
    return pose


def seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def interpolated(source, query):
    times = sorted(source)
    poses = np.array([source[stamp] for stamp in times])
    poses[:, 3] = np.unwrap(poses[:, 3])
    return np.array([np.interp(query, times, poses[:, axis]) for axis in range(4)]).T


def rpe(reference, odom):
    distances = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(reference[:, :2], axis=0), axis=1))]
    indices = np.searchsorted(distances, np.arange(0, distances[-1], 1.0))
    errors = []
    for first, last in zip(indices[:-1], indices[1:]):
        actual = rotation2(-reference[first, 3]) @ (reference[last, :2] - reference[first, :2])
        estimate = rotation2(-odom[first, 3]) @ (odom[last, :2] - odom[first, :2])
        errors.append(float(np.linalg.norm(estimate - actual) / (distances[last] - distances[first])))
    assert len(errors) >= 3, f"Insufficient actual path: {distances[-1]:.2f} m"
    return float(np.mean(errors)), float(distances[-1])


class Driver(Node):
    def __init__(self):
        super().__init__("t4_public_square")
        self.now = 0.0
        self.ready = False
        self.truth = {}
        self.odom = {}
        self.transforms = {}
        self.create_subscription(Clock, "/clock", self.clock, qos_profile_sensor_data)
        self.create_subscription(Bool, "/go1_ready", self.ready_message,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(Odometry, "/odom/ground_truth", self.reference, qos_profile_sensor_data)
        self.create_subscription(Odometry, "/odom", self.estimate, 100)
        self.create_subscription(TFMessage, "/tf", self.transforms_message, 100)
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)

    def clock(self, message):
        self.now = seconds(message.clock)

    def ready_message(self, message):
        self.ready = message.data

    def reference(self, message):
        pose = message.pose.pose
        self.truth[seconds(message.header.stamp)] = read_pose(pose.position, pose.orientation)

    def estimate(self, message):
        assert message.header.frame_id == "odom" and message.child_frame_id == "trunk"
        pose = message.pose.pose
        self.odom[seconds(message.header.stamp)] = read_pose(pose.position, pose.orientation)

    def transforms_message(self, message):
        for frame in message.transforms:
            if frame.header.frame_id == "odom" and frame.child_frame_id == "trunk":
                self.transforms[seconds(frame.header.stamp)] = read_pose(
                    frame.transform.translation, frame.transform.rotation)

    def drive(self, duration, speed=0.0, turn=0.0):
        command = Twist()
        command.linear.x = speed
        command.angular.z = turn
        target = self.now + duration
        last_publish = -1.0
        deadline = time.monotonic() + max(45, duration * 20)
        while self.now < target:
            if time.monotonic() > deadline:
                raise RuntimeError("Simulator clock stalled")
            if self.now >= last_publish + 0.048:
                self.publisher.publish(command)
                last_publish = self.now
            rclpy.spin_once(self, timeout_sec=0.02)


def main():
    rclpy.init()
    node = Driver()
    try:
        deadline = time.monotonic() + 180
        while not (node.ready and node.odom and node.truth and node.transforms):
            if time.monotonic() > deadline:
                raise RuntimeError(f"Startup: ready={node.ready}, odom={len(node.odom)}, "
                                   f"truth={len(node.truth)}, tf={len(node.transforms)}")
            rclpy.spin_once(node, timeout_sec=0.1)
        node.drive(2)
        start = node.now
        for _ in range(4):
            node.drive(6.8, speed=0.2)
            node.drive(math.pi / 0.6, turn=0.3)
        motion_end = node.now
        node.drive(3)
        rest = node.now
        node.drive(10.2)
        timestamps = np.array(sorted(node.odom))
        query = np.array([stamp for stamp in sorted(node.truth) if start <= stamp <= motion_end])
        error, distance = rpe(interpolated(node.truth, query), interpolated(node.odom, query))
        first, last = interpolated(node.odom, [rest, rest + 10])
        drift_m = float(np.linalg.norm(last[:3] - first[:3]))
        drift_deg = float(abs(math.degrees(last[3] - first[3])))
        shared = sorted(node.odom.keys() & node.transforms.keys())
        assert len(shared) > 750, "Missing paired odometry and TF timestamps"
        assert all(np.allclose(node.odom[stamp], node.transforms[stamp]) for stamp in shared)
        hz = float(sum(start <= stamp <= rest + 10 for stamp in timestamps) / (rest + 10 - start))
        result = dict(path_m=distance, rpe=error, rest_drift_m=drift_m,
                      rest_drift_deg=drift_deg, odom_hz=hz, paired_tf_samples=len(shared))
        print(json.dumps(result, indent=2), flush=True)
        assert hz >= 20 and error <= .50 and drift_m <= .10 and drift_deg <= 5.0
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
