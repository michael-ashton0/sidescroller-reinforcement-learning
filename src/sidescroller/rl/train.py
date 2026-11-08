"""Short, reproducible DQN training; with explicit experiment configuration."""
import argparse
import random
from dataclasses import replace
from sidescroller.experiments.config import load_config
from sidescroller.experiments.runs import create_run, append_metrics, write_json
from pathlib import Path
import numpy as np
import torch
from sidescroller.rl.model import DQN, ReplayBuffer
from sidescroller.env import ShooterEnv


def optimize(online, target, replay, batch_size=64, gamma=0.99):
    device = next(online.parameters()).device
    states, actions, rewards, next_states, terminated = (
        tensor.to(device) for tensor in replay.sample(batch_size))
    qvalues = online(states).gather(1, actions[:, None]).squeeze(1)
    with torch.no_grad():
        targets = rewards + gamma * target(next_states).max(1).values * (1 - terminated)
    return online.backpropagate(qvalues, targets)


def train_episode(env, online_net, stable_net, epsilon, replay, batch_size=64, seed=None, gamma=0.99):
    state, _ = env.reset(seed=seed)
    device = next(online_net.parameters()).device
    total_reward, losses = 0.0, []
    while True:
        if np.random.random() < epsilon:
            action = env.action_space.sample()
        else:
            with torch.no_grad():
                action = online_net(torch.as_tensor(state, device=device)[None]).argmax().item()
        next_state, reward, terminated, truncated, _ = env.step(action)
        # Time limits end interaction but still bootstrap from the final observation.
        replay.push((state, action, reward, next_state, terminated))
        total_reward += reward
        state = next_state
        if len(replay) >= batch_size:
            loss = optimize(online_net, stable_net, replay, batch_size, gamma)
            if not np.isfinite(loss):
                raise FloatingPointError(f'Nonfinite training loss: {loss}')
            losses.append(loss)
        if terminated or truncated:
            return dict(reward=total_reward, steps=env.step_count,
                        terminated=terminated, truncated=truncated, updates=len(losses),
                        loss=float(np.mean(losses)) if losses else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    for flag in ('episodes', 'max-steps', 'batch-size', 'seed'):
        parser.add_argument('--' + flag, type=int)
    parser.add_argument('--device')
    parser.add_argument('--output', type=Path, help='Optional additional weights export')
    parser.add_argument('--run-dir', type=Path, help='New run directory; must not already exist')
    parser.add_argument('--load', type=Path, help='Load weights only, not full training state')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        overrides = {key: getattr(args, key) for key in
                     ('episodes', 'max_steps', 'batch_size', 'seed', 'device')
                     if getattr(args, key) is not None}
        config = replace(config, training=replace(config.training, **overrides))
    except ValueError as exc:
        parser.error(str(exc))
    t = config.training
    random.seed(t.seed)
    np.random.seed(t.seed)
    torch.manual_seed(t.seed)
    torch.set_num_threads(t.torch_threads)
    directory = create_run(config, args.run_dir, args.config, args.load)
    env = None
    try:
        env = ShooterEnv(max_episode_steps=t.max_steps, reward_settings=config.reward)
        online = DQN(9, 7, lr_alpha=t.learning_rate).to(t.device)
        if args.load:
            online.load_state_dict(torch.load(args.load, map_location=t.device, weights_only=True))
        target = DQN(9, 7, lr_alpha=t.learning_rate).to(t.device)
        target.load_state_dict(online.state_dict())
        target.eval()
        replay = ReplayBuffer(t.replay_capacity)
        epsilon = t.epsilon_start
        for episode in range(1, t.episodes + 1):
            metrics = train_episode(env, online, target, epsilon, replay,
                                    t.batch_size, seed=t.seed + episode - 1, gamma=t.gamma)
            append_metrics(directory, dict(episode=episode, seed=t.seed + episode - 1,
                                           epsilon=epsilon, **metrics))
            print(f'Episode {episode}: {metrics} epsilon={epsilon:.3f}', flush=True)
            if episode % t.target_update_episodes == 0:
                target.load_state_dict(online.state_dict())
            epsilon = max(t.epsilon_min, epsilon * t.epsilon_decay)
        checkpoint = directory / 'checkpoints/final.pt'
        torch.save(online.state_dict(), checkpoint)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            torch.save(online.state_dict(), args.output)
        write_json(directory / 'result.json', {'status': 'complete', 'episodes': t.episodes,
                   'checkpoint': str(checkpoint),
                   'weights_export': str(args.output.resolve()) if args.output else None})
        print(f'Saved weights: {checkpoint}')
    except BaseException as exc:
        write_json(directory / 'result.json', {'status': 'failed', 'error': type(exc).__name__,
                                              'message': str(exc)})
        raise
    finally:
        if env is not None:
            env.close()


if __name__ == '__main__':
    main()
