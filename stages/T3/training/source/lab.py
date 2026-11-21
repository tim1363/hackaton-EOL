import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from actor import Actor
from go1_env import Config, Go1Env, RewardWeights


def make_env(scene, config):
    def create():
        return Go1Env(scene, config)

    return create


def rollout(env, predict, seed):
    obs, _ = env.reset(seed=seed)
    score = 0.0
    reached = False
    for step in range(env.horizon):
        obs, reward, fallen, timeout, info = env.step(predict(obs))
        score += reward
        reached = reached or (info["distance_m"] >= 3.0 and not fallen)
        if reached or fallen or timeout:
            return {
                "seed": seed,
                "seconds": (step + 1) / env.config.control_hz,
                "distance_m": round(info["distance_m"], 3),
                "fallen": fallen,
                "reached_3m": reached,
                "reward": round(score, 2),
            }
    raise RuntimeError("Episode did not stop at its configured horizon.")


def evaluate(scene, config, actor_path, seed, episodes):
    env = Go1Env(scene, config)
    if actor_path is None:
        def predict(_observations):
            return np.zeros(env.action_space.shape, dtype=np.float32)
    else:
        predict = Actor(actor_path).predict
    results = [rollout(env, predict, seed + index) for index in range(episodes)]
    env.close()
    return results


def export_actor(model, out, env, seed):
    from torch import nn

    sequence = tuple(model.policy.mlp_extractor.policy_net)
    if tuple(type(layer) for layer in sequence) != (nn.Linear, nn.Tanh, nn.Linear, nn.Tanh):
        raise ValueError("Export expects two tanh hidden layers.")
    layers = (sequence[0], sequence[2], model.policy.action_net)
    parameters = {}
    for index, layer in enumerate(layers):
        parameters[f"weight_{index}"] = layer.weight.detach().cpu().numpy()
        parameters[f"bias_{index}"] = layer.bias.detach().cpu().numpy()
    actor_path = out / "actor.npz"
    np.savez_compressed(actor_path, **parameters)
    batch = [env.reset(seed=seed)[0]]
    random = np.random.default_rng(seed)
    for _ in range(31):
        observation, _, fallen, timeout, _ = env.step(
            random.uniform(-0.2, 0.2, env.action_space.shape).astype(np.float32)
        )
        batch.append(observation)
        if fallen or timeout:
            env.reset()
    batch = np.asarray(batch)
    expected, _ = model.predict(batch, deterministic=True)
    actual = Actor(actor_path).predict(batch)
    np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-6)
    np.savez_compressed(out / "parity.npz", observations=batch, actions=expected)
    metadata = env.interface()
    metadata["export_max_abs_error"] = float(np.max(np.abs(actual - expected)))
    (out / "interface.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return actor_path


def read_config(run):
    settings = json.loads((run / "interface.json").read_text(encoding="utf-8"))["config"]
    reward = RewardWeights(**settings.pop("reward"))
    return Config(**settings, reward=reward)


def train(args, config):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecMonitor

    torch.set_num_threads(args.torch_threads)
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    sample = Go1Env(args.scene, config)
    n_steps = 512
    settings = {
        **sample.interface(),
        "training": {
            "seed": args.seed, "steps": args.steps, "workers": args.workers,
            "rollout_steps": n_steps, "learning_rate": args.learning_rate,
        },
    }
    (out / "config.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    factory = make_env(args.scene, config)
    if args.workers == 1:
        train_env = DummyVecEnv([lambda: Monitor(factory(), str(out / "training"))])
    else:
        train_env = VecMonitor(
            SubprocVecEnv([factory for _ in range(args.workers)], start_method="spawn"),
            str(out / "training"),
        )
    try:
        model = PPO(
            "MlpPolicy",
            train_env,
            device="cpu",
            n_steps=n_steps,
            batch_size=128,
            learning_rate=args.learning_rate,
            seed=args.seed,
            verbose=1,
        )
        checkpoint = CheckpointCallback(
            max(1, 16384 // args.workers), str(out / "checkpoints"), name_prefix="ppo"
        )
        model.learn(total_timesteps=args.steps, callback=checkpoint, log_interval=4)
        model.save(out / "ppo")
        actor_path = export_actor(model, out, sample, args.seed)
    finally:
        train_env.close()
        sample.close()
    results = evaluate(args.scene, config, actor_path, args.seed + 1000, args.episodes)
    (out / "evaluation.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Personal Go1 lab (simulation only).")
    parser.add_argument("mode", choices=("baseline", "train", "eval"))
    parser.add_argument("--scene", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--actor", type=Path)
    parser.add_argument("--speed", type=float, default=0.4)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--tracking-weight", type=float, default=RewardWeights.tracking)
    parser.add_argument("--objective", choices=("body", "course", "progress"), default="body")
    parser.add_argument("--gait-hz", type=float, default=0.0)
    parser.add_argument("--action-radius", type=float, default=Config.action_radius_rad)
    parser.add_argument("--servo-kp", type=float)
    parser.add_argument("--servo-kd", type=float, default=Config.servo_kd)
    parser.add_argument("--learning-rate", type=float, default=0.0003)
    parser.add_argument("--torch-threads", type=int, default=2)
    parser.add_argument("--scenario", choices=("nominal", "stress", "mixed"), default="nominal")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=32768)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()
    if not (0.1 <= args.speed <= 0.6 and args.seconds > 0 and args.tracking_weight > 0):
        parser.error("Require speed in [0.1, 0.6], positive seconds and positive tracking weight.")
    if min(args.steps, args.workers, args.episodes, args.torch_threads) < 1:
        parser.error("Require positive steps, workers and episodes.")
    if args.action_radius <= 0 or (args.servo_kp is not None and args.servo_kp <= 0) or args.servo_kd < 0:
        parser.error("Invalid action radius or servo gains.")
    if args.mode == "train" and args.out is None:
        parser.error("train requires --out")
    if args.mode == "eval" and args.actor is None:
        parser.error("eval requires --actor")
    config = Config(
        speed_mps=args.speed,
        episode_seconds=args.seconds,
        objective=args.objective,
        gait_hz=args.gait_hz,
        action_radius_rad=args.action_radius,
        servo_kp=args.servo_kp,
        servo_kd=args.servo_kd,
        scenario=args.scenario,
        reward=replace(RewardWeights(), tracking=args.tracking_weight),
    )
    if args.mode == "train":
        train(args, config)
    else:
        print(json.dumps(evaluate(args.scene, config, args.actor, args.seed, args.episodes), indent=2))


if __name__ == "__main__":
    main()
