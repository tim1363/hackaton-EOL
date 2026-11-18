#!/usr/bin/env python3
"""Initial LiDAR+IMU odometry prototype; not a validated T4 submission."""
import math

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Imu, LaserScan
from tf2_ros import Buffer, TransformBroadcaster, TransformException, TransformListener

from scan_match import (match_translation, quaternion_matrix, quaternion_multiply,
                        rotation2, yaw_of, yaw_quaternion)


def q_array(q):
    value = np.array([q.x, q.y, q.z, q.w], dtype=float)
    norm = np.linalg.norm(value)
    if not np.isfinite(norm) or norm < 1e-9:
        raise ValueError("invalid quaternion")
    return value / norm


class OdomPrototype(Node):
    def __init__(self):
        super().__init__('t4_scan_odom_prototype', parameter_overrides=[
            Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.broadcaster = TransformBroadcaster(self)
        self.publisher = self.create_publisher(Odometry, '/odom', 10)
        self.create_subscription(Imu, '/imu/data', self.on_imu, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(0.02, self.publish_odom)
        self.world_trunk = None
        self.reference_yaw = None
        self.previous_scan = None
        self.previous_yaw = None
        self.previous_stamp = None
        self.position = np.zeros(2)
        self.velocity = np.zeros(2)
        self.yaw_rate = 0.0

    def trunk_from(self, frame):
        if frame == 'trunk':
            return np.eye(3), np.zeros(3), np.array([0., 0., 0., 1.])
        transform = self.tf_buffer.lookup_transform('trunk', frame, Time()).transform
        q = q_array(transform.rotation)
        t = transform.translation
        return quaternion_matrix(q), np.array([t.x, t.y, t.z]), q

    def on_imu(self, msg):
        if msg.orientation_covariance[0] < 0 or not msg.header.frame_id:
            return
        try:
            _, _, trunk_imu = self.trunk_from(msg.header.frame_id)
            world_imu = q_array(msg.orientation)
            inverse = trunk_imu * np.array([-1., -1., -1., 1.])
            self.world_trunk = quaternion_multiply(world_imu, inverse)
        except (TransformException, ValueError):
            return

    def on_scan(self, msg):
        if self.world_trunk is None or not msg.header.frame_id:
            return
        try:
            sensor_rotation, sensor_offset, _ = self.trunk_from(msg.header.frame_id)
            yaw = yaw_of(self.world_trunk)
            level = quaternion_matrix(quaternion_multiply(yaw_quaternion(-yaw), self.world_trunk))
        except (TransformException, ValueError):
            return
        ranges = np.asarray(msg.ranges, dtype=float)
        mask = np.isfinite(ranges) & (ranges >= msg.range_min) & (ranges < msg.range_max)
        indices = np.flatnonzero(mask)
        if len(indices) < 20:
            return
        indices = indices[::max(1, math.ceil(len(indices) / 160))]
        angles = msg.angle_min + indices * msg.angle_increment
        points = np.column_stack((ranges[indices] * np.cos(angles),
                                  ranges[indices] * np.sin(angles), np.zeros(len(indices))))
        points = ((points @ sensor_rotation.T + sensor_offset) @ level.T)[:, :2]
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.previous_scan is None:
            self.reference_yaw = yaw
        elif stamp > self.previous_stamp:
            yaw_delta = math.atan2(math.sin(yaw - self.previous_yaw), math.cos(yaw - self.previous_yaw))
            delta = match_translation(self.previous_scan, points, yaw_delta)
            dt = stamp - self.previous_stamp
            if delta is not None:
                self.position += rotation2(self.previous_yaw - self.reference_yaw) @ delta
                self.velocity = rotation2(-yaw_delta) @ delta / dt
                self.yaw_rate = yaw_delta / dt
            else:
                self.velocity[:] = 0
                self.yaw_rate = 0.0
        self.previous_scan, self.previous_yaw, self.previous_stamp = points, yaw, stamp

    def publish_odom(self):
        if self.reference_yaw is None or self.world_trunk is None:
            return
        q = quaternion_multiply(yaw_quaternion(-self.reference_yaw), self.world_trunk)
        q /= np.linalg.norm(q)
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp, odom.header.frame_id, odom.child_frame_id = stamp, 'odom', 'trunk'
        odom.pose.pose.position.x, odom.pose.pose.position.y = map(float, self.position)
        odom.pose.pose.orientation.x, odom.pose.pose.orientation.y, odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = map(float, q)
        odom.twist.twist.linear.x, odom.twist.twist.linear.y = map(float, self.velocity)
        odom.twist.twist.angular.z = float(self.yaw_rate)
        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = odom.child_frame_id
        transform.transform.translation.x, transform.transform.translation.y = map(float, self.position)
        transform.transform.rotation = odom.pose.pose.orientation
        self.publisher.publish(odom)
        self.broadcaster.sendTransform(transform)


def main():
    rclpy.init()
    node = OdomPrototype()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
