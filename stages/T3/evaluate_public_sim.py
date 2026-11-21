"""Informal public-simulator T3 episode; ground truth is used only here.

This is not the organizer's Judge. It publishes a fixed /cmd_vel, observes
/odom/ground_truth for scoring, and measures /lowcmd simulation-time gaps.
"""
import os
from pathlib import Path
import json
import math

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from unitree_go.msg import LowCmd


def motor_targets(msg):
    return [float(m.q) for m in msg.motor_cmd[:12]]



class Episode(Node):
    def __init__(self):
        super().__init__("public_sim_t3_evaluation", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom/ground_truth", self.on_odom, 10)
        self.create_subscription(LowCmd, "/lowcmd", self.on_safe, 100)
        self.create_subscription(LowCmd, "/lowcmd_bare", self.on_bare, 100)
        self.create_timer(0.1, self.send_command)
        self.first_command_time = None
        self.start = None
        self.start_yaw = None
        self.bad_since = [None, None, None]
        self.last_safe_ns = None
        self.gaps = []
        self.bare_count = 0
        self.safe_count = 0
        self.result = None
        self.trace = []
        self.previous_target = None
        self.max_target_step = 0.0
        self.unchanged_safe_count = 0

    def send_command(self):
        msg = Twist()
        msg.linear.x = 0.4
        self.publisher.publish(msg)
        if self.first_command_time is None and self.publisher.get_subscription_count() and self.safe_count:
            self.first_command_time = self.get_clock().now().nanoseconds * 1e-9

    def on_safe(self, msg):
        now = self.get_clock().now().nanoseconds
        if self.last_safe_ns is not None and now >= self.last_safe_ns:
            self.gaps.append((now - self.last_safe_ns) * 1e-9)
        target = motor_targets(msg)
        if self.previous_target is not None:
            step = max(abs(a-b) for a, b in zip(target, self.previous_target))
            self.max_target_step = max(self.max_target_step, step)
            self.unchanged_safe_count += step < 1e-7
        self.previous_target = target
        if os.environ.get("GO1_EVAL_TRACE"):
            self.trace.append([now * 1e-9, "safe", target])
        self.last_safe_ns = now
        self.safe_count += 1

    def on_bare(self, msg):
        self.bare_count += 1
        if os.environ.get("GO1_EVAL_TRACE"):
            self.trace.append([self.get_clock().now().nanoseconds * 1e-9, "bare", motor_targets(msg)])

    def on_odom(self, msg):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        if os.environ.get("GO1_EVAL_TRACE"):
            self.trace.append([t, "pose", [p.x, p.y, p.z, q.w, q.x, q.y, q.z]])
        if self.first_command_time is None or t < self.first_command_time + 1.5:
            return
        roll = math.atan2(2*(q.w*q.x + q.y*q.z), 1-2*(q.x*q.x + q.y*q.y))
        pitch = math.asin(max(-1, min(1, 2*(q.w*q.y - q.z*q.x))))
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        if self.start is None:
            self.start = (p.x, p.y)
            self.start_yaw = yaw
            self.scored_start = t
        progress = ((p.x-self.start[0])*math.cos(self.start_yaw)
                    + (p.y-self.start[1])*math.sin(self.start_yaw))
        violations = (p.z < 0.16, abs(roll) > math.radians(50), abs(pitch) > math.radians(50))
        for index, bad in enumerate(violations):
            if not bad:
                self.bad_since[index] = None
            elif self.bad_since[index] is None:
                self.bad_since[index] = t
        fallen = any(start is not None and t - start > 0.5 for start in self.bad_since)
        elapsed = t - self.scored_start
        if fallen or progress >= 3.0 or elapsed >= 90.0:
            self.result = {
                "success": bool(progress >= 3.0 and not fallen), "fallen": bool(fallen),
                "progress_m": progress, "scored_time_s": elapsed,
                "speed_command_mps": 0.4, "safe_count": self.safe_count,
                "bare_count": self.bare_count,
                "max_observed_safe_gap_s": max(self.gaps, default=None),
                "max_safe_target_step_rad": self.max_target_step,
                "unchanged_safe_count": self.unchanged_safe_count,
                "note": "informal public simulator; ground truth only for evaluation",
            }


def main():
    rclpy.init()
    node = Episode()
    try:
        while rclpy.ok() and node.result is None:
            rclpy.spin_once(node, timeout_sec=1.0)
        print("PUBLIC_T3_RESULT=" + json.dumps(node.result, sort_keys=True), flush=True)
        if os.environ.get("GO1_EVAL_TRACE"):
            Path(os.environ["GO1_EVAL_TRACE"]).write_text(json.dumps(node.trace))
        if node.result is None:
            raise RuntimeError("Simulator ended before a result")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
