
import numpy as np
import torch
from dqn_model import DQN, ReplayBuffer
from dqn_render import visualize_episode
from gymenv import ShooterEnv

GAMMA = 0.99             # Discount factor highly values future reward
EPSILON_START = 1.0      # Begin with 100% random exploration
EPSILON_DECAY = 0.995    # Decay slowly
EPSILON_MIN = 0.05       # Never fully stop exploring
TARGET_UPDATE_FREQ = 10  # How often to reload stable_net from online_net
TARGET_RENDER_FREQ = 1000  # How often to render the agent during training
BATCH_SIZE = 64          # Balance learning with efficiency
MAX_EPISODES = 64_000    # 64k ought to be enough for anybody! :)

# Global variable holding CPU/GPU status
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def train_episode(env:ShooterEnv, 
                  online_net:DQN, 
                  stable_net:DQN, 
                  epsilon:float, 
                  replay:ReplayBuffer):
    '''
    Runs a single episode of interaction with the environment and trains the 
    Q-network using experience replay and target Q-value updates.

    Parameters:
    - env (ShooterEnv): The game environment.
    - train_net (DQN): The Q-network being actively trained.
    - stable_net (DQN): The target Q-network used for stable Q-value estimation.
    - epsilon (float): Current epsilon value for epsilon-greedy exploration.
    - replay (ReplayBuffer): Memory buffer storing past experiences.

    Returns:
    - float: Total reward accumulated during the episode.
    '''

    # Initialize this episode with the observation (state) being the input
    # to the neural network (a tensor).
    state, info = env.reset()
    state = torch.from_numpy(state).unsqueeze(0).float().to(device)
    done = False
    total_reward = 0

    # Play this episode out and train the model as you go.
    while not done:

        # Choose the next action (get an action, don't track gradients).
        if np.random.rand() < epsilon:
            action = env.action_space.sample()
        else:
            with torch.no_grad():
                q_vals = online_net(state)
                action = q_vals.argmax().item()

        # Take a step forward in the game environment.
        nstate, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward

        # Add this step to our replay buffer and convert to a torch object.
        #replay.push((state.numpy(), action, reward, next_state, done))
        replay.push((state, action, reward, nstate, done))
        state = torch.from_numpy(nstate).unsqueeze(0).float().to(device)

        # Don't train the network until we have enough experiences.
        if len(replay) < BATCH_SIZE:
            continue

        # Take a 'replay buffer' worth of states and run through NN.
        states, actions, rewards, next_states, dones = replay.sample(BATCH_SIZE)
        states = states.to(device)
        actions = actions.unsqueeze(1).to(device)
        rewards = rewards.to(device)
        next_states = next_states.to(device)
        dones = dones.to(device)
        qvals = online_net(states).gather(1, actions).squeeze()

        # Compute the current Q-Values using stable network as 
        # (but don't track gradients yet)
        with torch.no_grad():
            next_qvals = stable_net(next_states).max(1)[0]
            targets = rewards + GAMMA * next_qvals * (1 - dones)

        # Train online NN (q_net) using gradient descent
        online_net.backpropagate(qvals, targets)

    # Total reward helps monitor progress
    return total_reward


def main():
    '''
    Trains a Deep Q-Learning neural network to play the custom shooter game
    using experience replay and a target network for stability.
    '''

    epsilon = EPSILON_START
    env_headless = ShooterEnv(render_mode=None)
    obs_size = env_headless.observation_space.shape[0]
    n_actions = env_headless.action_space.n
    print(f"Creating online and stable neural networks "
          f"({n_actions} actions / {obs_size} observation vars)")

    # Online and stable networks with the stable version being a copy of the
    # online version that is refreshed slowly to maintain learning stability.
    online_net = DQN(obs_size, n_actions)
    stable_net = DQN(obs_size, n_actions)
    online_net.to(device)
    stable_net.to(device)
    stable_net.load_state_dict(online_net.state_dict())

    # Use ADAM gradient descent and a replay buffer to store state transitions.
    replay = ReplayBuffer()

    # Main learning loop, going through each episode one at a time.
    print(f"Training started...")
    for episode in range(1, MAX_EPISODES):
        
        # Train the neural networks.
        online_net.train()
        stable_net.train()
        reward = train_episode(env_headless, 
                               online_net, 
                               stable_net, 
                               epsilon, 
                               replay)

        # Update target network (the stable network) every X episodes.
        if episode > 0 and episode % TARGET_UPDATE_FREQ == 0:
            print(f"(updated stable network with latest from online network)")
            stable_net.load_state_dict(online_net.state_dict())

        # Report on the learning progress (and render agent every x episodes).
        if episode > 0 and episode % TARGET_RENDER_FREQ == 0:
            print(f"\n>> Visualizing agent at episode {episode} <<\n")
            visualize_episode(online_net, device)
            torch.save(online_net.state_dict(), f'dqn_shooter_{episode}.pt')
        print(f"Episode {episode:>6} | "
              f"Reward: {reward:>10.2f} | "
              f"Epsilon: {epsilon:.3f}")

        # Epsilon greedy decay
        epsilon = max(EPSILON_MIN, epsilon * EPSILON_DECAY)

    # All done, close out the environment
    filename = 'dqn_shooter_final.pt'
    torch.save(online_net.state_dict(), filename)
    print(f"\nTraining complete. Final model saved as '{filename}'\n")
    env_headless.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCtrl+C detected... bye for now.\n")
