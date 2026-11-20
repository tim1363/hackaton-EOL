"""Black-box ROS exercise of the T2 node with a synthetic simulation clock.

Runs independently of the robot simulator. It checks the published stream, not
private node state. This is a regression test, not the organizer's Judge.
"""
import copy
import json
import math
import os
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from unitree_go.msg import LowCmd

from safety_core import HOME, LOWER, UPPER, CollisionChecker, TargetFilter

DT_NS = 10_000_000
# Set equal to DT_NS for roughly real-time clock advancement. The actual wall
# rate can be slower due to scheduling and Python/ROS overhead.
WALL_TICK = float(os.environ.get("T2_TEST_WALL_TICK", "0.02"))
if not math.isfinite(WALL_TICK) or WALL_TICK <= 0:
    raise ValueError("T2_TEST_WALL_TICK must be positive and finite")
FIELDS = ("q", "dq", "tau", "kp", "kd")


def command():
    msg = LowCmd()
    for i, motor in enumerate(msg.motor_cmd[:12]):
        motor.mode = 0x0A
        motor.q = float(HOME[i] + 0.02)
        motor.dq = 1.0
        motor.tau = 1.0
        motor.kp = 35.0
        motor.kd = 0.5
    return msg


class Driver(Node):
    def __init__(self):
        super().__init__("t2_black_box_test")
        self.clock_pub = self.create_publisher(Clock, "/clock", 10)
        self.input_pub = self.create_publisher(LowCmd, "/lowcmd_bare", 10)
        self.create_subscription(LowCmd, "/lowcmd", self.output, 100)
        self.now_ns = 0
        self.samples = []

    def output(self, msg):
        self.samples.append((self.now_ns, copy.deepcopy(msg)))

    def advance(self, msg=None):
        self.now_ns += DT_NS
        clock = Clock()
        clock.clock.sec, clock.clock.nanosec = divmod(self.now_ns, 1_000_000_000)
        self.clock_pub.publish(clock)
        if msg is not None:
            self.input_pub.publish(msg)
        deadline = time.monotonic() + WALL_TICK
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.002, max(0.0, deadline - time.monotonic())))

    def run_phase(self, ticks, msg=None):
        start = self.now_ns
        for _ in range(ticks):
            self.advance(msg)
        return start, self.now_ns


def values(msg, field):
    return np.array([getattr(m, field) for m in msg.motor_cmd[:12]])


def phase_samples(driver, window, trim_ns=30_000_000):
    start, end = window
    result = [m for t, m in driver.samples if start + trim_ns <= t <= end - trim_ns]
    assert result, f"No output observed in interval {window}"
    return result


def run():
    rclpy.init()
    driver = Driver()
    try:
        deadline = time.monotonic() + 10
        while driver.input_pub.get_subscription_count() == 0:
            if time.monotonic() > deadline:
                raise RuntimeError("T2 subscriber not discovered")
            rclpy.spin_once(driver, timeout_sec=0.05)
        # Give the /clock and /lowcmd DDS endpoints time to discover each other.
        time.sleep(1.0)
        driver.run_phase(40, command())
        baseline = command()
        expected = values(baseline, "q")
        np.testing.assert_allclose(values(phase_samples(driver, (200_000_000, 400_000_000))[-1], "q"), expected, atol=1e-6)

        invalid_cases = []
        for index in (0, 19):
            for field in FIELDS:
                for invalid in (float("nan"), float("inf"), -float("inf")):
                    driver.run_phase(10, baseline)
                    bad = copy.deepcopy(baseline)
                    # The valid target is different, so accepting a partially
                    # sanitized bad message is observable even for unused motors.
                    bad.motor_cmd[0].q += 0.04
                    setattr(bad.motor_cmd[index], field, invalid)
                    window = driver.run_phase(14, bad)
                    for output in phase_samples(driver, window):
                        np.testing.assert_allclose(values(output, "q"), expected, atol=1e-6)
                        np.testing.assert_allclose(values(output, "dq"), 1.0, atol=1e-6)
                        np.testing.assert_allclose(values(output, "tau"), 1.0, atol=1e-6)
                    invalid_cases.append(f"motor[{index}].{field}={invalid}")

        # Drive toward a deterministically found collision boundary. Predict the
        # first rejected target with the same core, then check the ROS stream
        # actually reaches and holds it. This is not an independent model check.
        driver.run_phase(15, baseline)
        start = values(phase_samples(driver, (driver.now_ns - 100_000_000, driver.now_ns))[-1], "q")
        unsafe = copy.deepcopy(baseline)
        collision_goal = [0.44114418, 4.26371914, -0.99392088,
                          0.38092168, 3.10603050, -1.47268822,
                          0.08442751, 0.82383988, -1.99756924,
                          0.69448577, 4.47265256, -1.17518502]
        for motor, target in zip(unsafe.motor_cmd[:12], collision_goal):
            motor.q = target
        checker = CollisionChecker()
        expected_filter = TargetFilter(checker, start)
        for attempt in range(60):
            collision_hold, accepted = expected_filter.apply(values(unsafe, "q"))
            if not accepted:
                break
        assert not accepted and attempt > 0, "collision trajectory did not reach an unsafe transition"
        collision_window = driver.run_phase(100, unsafe)
        for output in phase_samples(driver, (collision_window[1] - 300_000_000, collision_window[1])):
            np.testing.assert_allclose(values(output, "q"), collision_hold, atol=3e-6)


        # Repeated extreme requests exercise limits and the 5-degree cap under
        # collision-checking load. Rejection is legal; at least one output must
        # progress for an otherwise valid, modest input (verified above).
        driver.run_phase(15, baseline)
        extreme = copy.deepcopy(baseline)
        for i, motor in enumerate(extreme.motor_cmd[:12]):
            motor.q = 1000.0 if i % 2 else -1000.0
        stress_wall_start = time.monotonic()
        stress = driver.run_phase(510, extreme)
        stress_wall_seconds = time.monotonic() - stress_wall_start
        driver.run_phase(40, baseline)
        before_watchdog = phase_samples(driver, (driver.now_ns - 150_000_000, driver.now_ns))[-1]
        held_target = values(before_watchdog, "q")
        last_input_ns = driver.now_ns
        driver.run_phase(80)
        held = [t for t, output in driver.samples if t >= last_input_ns
                and np.all(values(output, "dq") == 0) and np.all(values(output, "tau") == 0)]
        assert held, "watchdog did not enter hold"
        watchdog_delay = (held[0] - last_input_ns) / 1e9
        assert watchdog_delay <= 0.5, f"watchdog delay {watchdog_delay:.3f}s"
        after = phase_samples(driver, (driver.now_ns - 250_000_000, driver.now_ns))
        for output in after:
            np.testing.assert_allclose(values(output, "q"), held_target, atol=1e-6)
            np.testing.assert_array_equal(values(output, "dq"), 0.0)
            np.testing.assert_array_equal(values(output, "tau"), 0.0)

        timestamps = np.array([t for t, _ in driver.samples], dtype=np.int64)
        assert len(timestamps) > 2
        gaps = np.diff(timestamps) / 1e9
        assert gaps.max() <= 0.1 + 1e-9, f"output gap {gaps.max():.3f}s"
        # Five seconds entirely within the repeated extreme-input stress phase.
        window_start = stress[0] + 50_000_000
        window_count = sum(window_start <= t < window_start + 5_000_000_000 for t in timestamps)
        assert window_count / 5 >= 50, f"stress rate {window_count / 5:.1f}Hz"
        checker = CollisionChecker()
        previous = None
        for _, output in driver.samples:
            assert all(math.isfinite(getattr(m, f)) for m in output.motor_cmd for f in FIELDS)
            q = values(output, "q")
            assert np.all(q >= LOWER) and np.all(q <= UPPER), f"joint limit: {q}"
            if previous is not None:
                assert np.max(np.abs(q - previous)) <= math.radians(5) + 1e-7
                assert checker.safe_transition(previous, q), "unsafe transition"
            else:
                assert checker.safe(q), "unsafe initial target"
            previous = q
        print(json.dumps({"result": "PASS", "invalid_cases": len(invalid_cases),
                          "collision_rejected_after_safe_steps": attempt,
                          "outputs": len(driver.samples), "five_second_hz": window_count / 5,
                          "max_observed_gap_s": float(gaps.max()),
                          "stress_sim_seconds": (stress[1] - stress[0]) / 1e9,
                          "stress_wall_seconds": stress_wall_seconds,
                          "requested_wall_tick_s": WALL_TICK,
                          "observed_watchdog_delay_s": watchdog_delay}, indent=2), flush=True)
    finally:
        driver.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    run()
