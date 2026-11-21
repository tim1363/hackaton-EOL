"""Inference for a Go1 actor trained to correct a periodic trot."""
import json
import math
from pathlib import Path

import numpy as np


class ResidualPolicy:
    def __init__(self, directory):
        directory = Path(directory)
        interface = json.loads((directory / "interface.json").read_text(encoding="utf-8"))
        settings = interface["config"]
        self.home = np.asarray(interface["home_rad"], dtype=np.float32)
        self.gait_hz = float(settings["gait_hz"])
        self.rate = int(settings["control_hz"])
        self.radius = float(settings["action_radius_rad"])
        self.kp = float(settings["servo_kp"])
        self.kd = float(settings["servo_kd"])
        width = 43 + 2 * bool(self.gait_hz)
        with np.load(directory / "actor.npz", allow_pickle=False) as weights:
            self.layers = [(weights[f"weight_{index}"], weights[f"bias_{index}"]) for index in range(3)]
        for weight, bias in self.layers:
            if (weight.ndim != 2 or weight.shape[1] != width or bias.shape != (weight.shape[0],)
                    or not np.isfinite(weight).all() or not np.isfinite(bias).all()):
                raise ValueError("Unexpected actor layers")
            width = weight.shape[0]
        if width != 12 or self.home.shape != (12,) or not np.isfinite(self.home).all():
            raise ValueError("Expected twelve joints")
        if (not np.isfinite([self.gait_hz, self.kp, self.kd, self.radius]).all() or self.rate != 50
                or not 0 < self.kp <= 100 or not 0 <= self.kd <= 10 or not 0 < self.radius <= 1
                or not 0 <= self.gait_hz <= 4):
            raise ValueError("Unsupported servo or training settings")
        self.previous = np.zeros(12, dtype=np.float32)
        self.steps = 0

    def action(self, observations):
        result = np.asarray(observations, dtype=np.float32)
        for index, (weight, bias) in enumerate(self.layers):
            result = result @ weight.T + bias
            if index < len(self.layers) - 1:
                result = np.tanh(result)
        return np.clip(result, -1, 1)

    def target(self, quaternion, gyro, positions, velocities, speed):
        if speed <= 0:
            self.previous.fill(0)
            self.steps = 0
            return self.home
        norm = np.linalg.norm(quaternion)
        if not np.isfinite(norm) or norm < 1e-8:
            raise ValueError("Invalid IMU orientation")
        w, x, y, z = np.asarray(quaternion) / norm
        up = [2 * (x*z - w*y), 2 * (y*z + w*x), 1 - 2 * (x*x + y*y)]
        phase = 2 * math.pi * self.gait_hz * self.steps / self.rate
        observations = np.concatenate((up, gyro, [speed], np.asarray(positions) - self.home,
                                       velocities, self.previous,
                                       [math.sin(phase), math.cos(phase)] if self.gait_hz else []))
        if not np.isfinite(observations).all():
            raise ValueError("Non-finite observation")
        nominal = self.home.copy()
        if self.gait_hz:
            legs = phase + np.array([0., math.pi, math.pi, 0.])
            swing = np.sin(legs)
            lift = np.maximum(0, np.cos(legs))
            nominal[1::3] += -0.22 * swing + 0.16 * lift
            nominal[2::3] -= 0.32 * lift
        self.previous = self.action(observations)
        self.steps += 1
        return nominal + self.radius * self.previous
