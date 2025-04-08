from gymenv import ShooterEnv
import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import random
from collections import deque
import time

# Learning and Network vars
gamma = 0.99
epsilon = 1.0
eps_decay = 0.995
min_epsilon = 0.05
target_update_freq = 10
batch_size = 64
max_episodes = 64000

class DeepQNetwork(nn.Module):
    def __init__(self, obs_size, n_actions):
        super().__init__()
        self.fc1 = nn.Linear(obs_size, 16)
        self.out = nn.Linear(16, n_actions)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.out(x)

class ReplayBuffer:
    def __init__(self, capacity=100_000):
        self.buffer = deque(maxlen=capacity)

    def push(self, transition):
        self.buffer.append(transition)
    
    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            torch.tensor(np.array(states), dtype=torch.float32),
            torch.tensor(actions, dtype=torch.int64),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.array(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32)
        )
    
    def __len__(self):
        return len(self.buffer)

def train_episode(env, live_net, stable_net, replay, optimizer):
    state, info = env.reset()
    state = torch.tensor(state, dtype=torch.float32)
    done = False
    total_reward = 0

    while not done:
        if np.random.rand() < epsilon:
            action = env.action_space.sample()
        else:
            with torch.no_grad():
                q_vals = live_net(state.unsqueeze(0))
                action = q_vals.argmax().item()
        
        next_state,reward,terminated,truncated,info =env.step(action)
        done = terminated or truncated
        total_reward += reward

        replay.push((state.numpy(), action, reward, next_state, done))
        state = torch.tensor(next_state, dtype=torch.float32)

        if len(replay) >= batch_size:
            state, actions, rewards, next_states, dones = (
                replay.sample(batch_size)
            )
        q_vals = (
            live_net(states).gather(1, actions.unsqeeze(1)).squeeze()
        )

        with torch.no_grad():
            next_q_values = stable_net(next_states.max(1))[0]
            targets = rewards + gamma * next_q_values * (1-dones)

        loss = F.mse_loss(q_vals, targets)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    return total_reward

def tain_dqn():

    global epsilon
    env = ShooterEnv(render_mode=None)
    obs_size = env.observation_space.shape[0]
    n_actions = env.action_space.n

    print(f'Creating online and stable neural networks')
    print(f'{n_actions} actions / {obs_size} observations')

    live_net = DeepQNetwork(obs_size, n_actions)
    stable_net = DeepQNetwork(obs_size, n_actions)
    stable_net.load_state_dict(live_net.state_dict())

    optimizer = optim.Adam(live_net.parameters(), lr=1e-4)
    replay = ReplayBuffer()

    for episode in range(1, max_episodes):
        live_net.train()
        stable_net.train()
        total_reward = train_episode(
            env, live_net, stable_net, replay, optimizer
        )

        if episode % target_update_freq == 0:
            print(f'(updated stable network with latest from online network)')
            stable_net.load_state_dict(live_net.state_dict())

        if episode > 0 and episode % 1000 == 0:
            print(f'\n>> Visualizing agent at epsiode {episode}\n')
            visualize_episode(live_net)
            torch.save(live_net.state_dict(), f'dqn_shooter_{episode}.pt')
        print(f'Episode {episode:>6} | '
                f'Reward: {total_reward:>10.2f} | '
                f'Epsilon: {epsilon:.3f}')
        
        epsilon = max(min_epsilon, epsilon * eps_decay)

    env.close()