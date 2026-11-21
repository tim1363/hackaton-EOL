from dataclasses import asdict, dataclass, field
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np


JOINTS = tuple(
    f"{leg}_{joint}"
    for leg in ("FR", "FL", "RR", "RL")
    for joint in ("hip", "thigh", "calf")
)
OBSERVATION_FIELDS = (
    ("body_up_xyz", 3),
    ("body_angular_velocity_rad_s", 3),
    ("requested_forward_speed_mps", 1),
    ("joint_position_offset_rad", 12),
    ("joint_velocity_rad_s", 12),
    ("previous_action", 12),
)
OBSERVATION_SIZE = sum(size for _, size in OBSERVATION_FIELDS)


@dataclass(frozen=True)
class RewardWeights:
    tracking: float = 1.5
    upright: float = 0.15
    lateral: float = 0.20
    turning: float = 0.12
    effort: float = 0.025
    jerk: float = 0.04
    fall: float = 2.0


@dataclass(frozen=True)
class Config:
    speed_mps: float = 0.4
    control_hz: int = 50
    episode_seconds: float = 15.0
    action_radius_rad: float = 0.60
    max_target_step_rad: float = np.deg2rad(5.0)
    objective: str = "body"
    gait_hz: float = 0.0
    scenario: str = "nominal"
    servo_kp: float | None = None
    servo_kd: float = 0.5
    reward: RewardWeights = field(default_factory=RewardWeights)


class Go1Env(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, scene: Path, config: Config = Config()):
        self.config = config
        self.model = mujoco.MjModel.from_xml_path(str(scene))
        self.data = mujoco.MjData(self.model)
        self.trunk = self.model.body("trunk").id
        self.home_key = self.model.key("home").id
        self.actuators = np.array([self.model.actuator(name).id for name in JOINTS])
        joint_ids = self.model.actuator_trnid[self.actuators, 0]
        self.position_indices = self.model.jnt_qposadr[joint_ids]
        self.velocity_indices = self.model.jnt_dofadr[joint_ids]
        self.home = self.model.key_qpos[self.home_key, self.position_indices].copy()
        self.limits = self.model.actuator_ctrlrange[self.actuators].copy()
        self.torque_limits = self.model.actuator_forcerange[self.actuators].copy()
        if config.servo_kp is not None:
            self.model.actuator_gainprm[:, 0] = 0
            self.model.actuator_biasprm[:, :] = 0
        self.floor = self.model.geom("floor").id
        self.floor_friction = self.model.geom_friction[self.floor].copy()
        self.fields = OBSERVATION_FIELDS + (
            (("gait_phase_sin_cos", 2),) if config.gait_hz else ()
        )
        self.frames = round(1 / (self.model.opt.timestep * config.control_hz))
        if not np.isclose(self.frames * self.model.opt.timestep, 1 / config.control_hz):
            raise ValueError("The scene timestep must divide the control interval.")
        self.horizon = round(config.episode_seconds * config.control_hz)
        self.action_space = gym.spaces.Box(-1, 1, (len(JOINTS),), dtype=np.float32)
        self.observation_space = gym.spaces.Box(
            -np.inf, np.inf, (sum(size for _, size in self.fields),), dtype=np.float32
        )
        self.body_velocity = np.empty(6)
        self.previous = np.zeros(len(JOINTS), dtype=np.float32)
        self.target = self.home.copy()
        self.steps = 0

    def _state(self):
        mujoco.mj_objectVelocity(
            self.model, self.data, mujoco.mjtObj.mjOBJ_BODY, self.trunk, self.body_velocity, 1
        )
        up = self.data.xmat[self.trunk].reshape(3, 3)[2]
        return up, self.body_velocity

    def _observation(self, up, velocity):
        phase = 2 * np.pi * self.config.gait_hz * self.steps / self.config.control_hz
        return np.concatenate(
            (
                up,
                velocity[:3],
                [self.config.speed_mps],
                self.data.qpos[self.position_indices] - self.home,
                self.data.qvel[self.velocity_indices],
                self.previous,
                [np.sin(phase), np.cos(phase)] if self.config.gait_hz else [],
            ),
            dtype=np.float32,
        )

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.home_key)
        stress = self.config.scenario == "stress" or (
            self.config.scenario == "mixed" and self.np_random.random() < 0.5
        )
        self.stress = stress
        spread = 0.04 if stress else 0.015
        self.data.qpos[self.position_indices] += self.np_random.uniform(-spread, spread, len(JOINTS))
        self.model.geom_friction[self.floor] = self.floor_friction
        if stress:
            self.model.geom_friction[self.floor, 0] *= self.np_random.uniform(0.60, 1.30)
            self.push_step = int(self.np_random.integers(80, 160))
            self.push_velocity = self.np_random.uniform(-0.28, 0.28, 2)
        self.target = self.home.copy()
        self.previous.fill(0)
        self.steps = 0
        self.data.ctrl[self.actuators] = self.target
        mujoco.mj_forward(self.model, self.data)
        self._advance(10 * self.frames)
        mujoco.mj_forward(self.model, self.data)
        self.origin = self.data.xpos[self.trunk].copy()
        self.heading = self.data.xmat[self.trunk].reshape(3, 3)[:2, 0].copy()
        self.heading /= np.linalg.norm(self.heading)
        self.distance = 0.0
        return self._observation(*self._state()), {}

    def _advance(self, frames):
        gain = self.config.servo_kp
        if gain is None:
            mujoco.mj_step(self.model, self.data, nstep=frames)
            return
        for _ in range(frames):
            errors = self.target - self.data.qpos[self.position_indices]
            velocity = self.data.qvel[self.velocity_indices]
            torque = gain * errors - self.config.servo_kd * velocity
            self.data.qfrc_applied[self.velocity_indices] = np.clip(
                torque, self.torque_limits[:, 0], self.torque_limits[:, 1]
            )
            mujoco.mj_step(self.model, self.data)

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        if action.shape != self.action_space.shape or not np.isfinite(action).all():
            raise ValueError("Expected 12 finite actions.")
        bounded = np.clip(action, -1, 1)
        delta_action = bounded - self.previous
        nominal = self.home.copy()
        if self.config.gait_hz:
            phase = 2 * np.pi * self.config.gait_hz * self.steps / self.config.control_hz
            swing = np.sin(phase + np.array([0.0, np.pi, np.pi, 0.0]))
            lift = np.maximum(0.0, np.cos(phase + np.array([0.0, np.pi, np.pi, 0.0])))
            nominal[1::3] += -0.22 * swing + 0.16 * lift
            nominal[2::3] -= 0.32 * lift
        desired = np.clip(
            nominal + bounded * self.config.action_radius_rad,
            self.limits[:, 0],
            self.limits[:, 1],
        )
        self.target += np.clip(
            desired - self.target, -self.config.max_target_step_rad, self.config.max_target_step_rad
        )
        self.data.ctrl[self.actuators] = self.target
        if self.stress and self.steps == self.push_step:
            self.data.qvel[:2] += self.push_velocity
        self._advance(self.frames)
        mujoco.mj_forward(self.model, self.data)
        self.steps += 1
        self.previous = bounded

        up, velocity = self._state()
        position = self.data.xpos[self.trunk]
        displacement = position[:2] - self.origin[:2]
        distance = float(displacement @ self.heading)
        fallen = bool(position[2] < 0.16 or up[2] < np.cos(np.deg2rad(50)))
        weights = self.config.reward
        speed_error = velocity[3] - self.config.speed_mps
        if self.config.objective in {"course", "progress"}:
            course_speed = (distance - self.distance) * self.config.control_hz
            direction = self.data.xmat[self.trunk].reshape(3, 3)[:2, 0]
            lateral_error = displacement @ np.array([-self.heading[1], self.heading[0]])
            if self.config.objective == "progress":
                tracking = (
                    np.clip(course_speed / self.config.speed_mps, -1.0, 1.0)
                    - 0.40 * np.clip(abs(lateral_error), 0.0, 2.0)
                    - 0.30 * (1.0 - direction @ self.heading)
                )
            else:
                tracking = (
                    np.clip(course_speed / self.config.speed_mps, -2.0, 1.0)
                    - 0.4 * abs(course_speed - self.config.speed_mps)
                    - 0.3 * (1.0 - direction @ self.heading)
                    - 0.2 * abs(lateral_error)
                )
        else:
            tracking = np.exp(-((speed_error / 0.35) ** 2))
        reward = (
            weights.tracking * tracking
            + weights.upright * up[2]
            - weights.lateral * velocity[4] ** 2
            - weights.turning * velocity[2] ** 2
            - weights.effort * np.mean(bounded ** 2)
            - weights.jerk * np.mean(delta_action ** 2)
            - weights.fall * fallen
        )
        self.distance = distance
        return (
            self._observation(up, velocity),
            float(reward),
            fallen,
            self.steps >= self.horizon,
            {"distance_m": distance, "forward_speed_mps": float(velocity[3]), "fallen": fallen},
        )

    def interface(self):
        return {
            "version": 1,
            "joints": list(JOINTS),
            "observations": list(self.fields),
            "action": "clip to [-1, 1], scale about nominal pose, clip joint limits, limit target delta",
            "home_rad": self.home.tolist(),
            "control_limits_rad": self.limits.tolist(),
            "config": asdict(self.config),
        }
