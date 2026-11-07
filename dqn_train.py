"""Short, reproducible DQN training; run from the repository root."""
import argparse
import random
from pathlib import Path
import numpy as np
import torch
from dqn_model import DQN, ReplayBuffer
from gymenv import ShooterEnv
from settings import DEFAULT_EPISODE_STEPS


def optimize(online, target, replay, batch_size=64, gamma=0.99):
    device = next(online.parameters()).device
    states, actions, rewards, next_states, terminated = (
        tensor.to(device) for tensor in replay.sample(batch_size))
    qvalues = online(states).gather(1, actions[:, None]).squeeze(1)
    with torch.no_grad():
        targets = rewards + gamma * target(next_states).max(1).values * (1 - terminated)
    return online.backpropagate(qvalues, targets)


def train_episode(env, online_net, stable_net, epsilon, replay, batch_size=64, seed=None):
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
            loss = optimize(online_net, stable_net, replay, batch_size)
            if not np.isfinite(loss):
                raise FloatingPointError(f'Nonfinite training loss: {loss}')
            losses.append(loss)
        if terminated or truncated:
            return dict(reward=total_reward, steps=env.step_count,
                        terminated=terminated, truncated=truncated, updates=len(losses),
                        loss=float(np.mean(losses)) if losses else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episodes', type=int, default=2)
    parser.add_argument('--max-steps', type=int, default=DEFAULT_EPISODE_STEPS)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--output', type=Path, default=Path('checkpoints/dqn_smoke.pt'))
    parser.add_argument('--load', type=Path)
    args = parser.parse_args()
    if min(args.episodes, args.max_steps, args.batch_size) <= 0:
        parser.error('episodes, max-steps and batch-size must be positive')
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(1)
    env = ShooterEnv(max_episode_steps=args.max_steps)
    try:
        online = DQN(9, 7).to(args.device)
        if args.load:
            online.load_state_dict(torch.load(args.load, map_location=args.device, weights_only=True))
        target = DQN(9, 7).to(args.device)
        target.load_state_dict(online.state_dict())
        target.eval()
        replay = ReplayBuffer()
        epsilon = 1.0
        for episode in range(1, args.episodes + 1):
            metrics = train_episode(env, online, target, epsilon, replay,
                                    args.batch_size, seed=args.seed + episode - 1)
            print(f'Episode {episode}: {metrics} epsilon={epsilon:.3f}', flush=True)
            if episode % 10 == 0:
                target.load_state_dict(online.state_dict())
            epsilon = max(0.05, epsilon * 0.995)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(online.state_dict(), args.output)
        print(f'Saved weights: {args.output}')
    finally:
        env.close()


if __name__ == '__main__':
    main()
