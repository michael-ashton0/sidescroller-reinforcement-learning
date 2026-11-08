
import argparse
from sidescroller.experiments.config import load_config
import time
import torch
import pygame
from sidescroller.env import ShooterEnv
from sidescroller.rl.model import DQN
from sidescroller.settings import FPS


def visualize_episode(model:DQN=None, 
                      #env:ShooterEnv, 
                      device:str='cpu', config=None):
    '''
    Renders a single episode of the custom Shooter environment using a 
    pre-trained DQN agent.

    Parameters:
    - model (torch.nn.Module): The trained DQN model used to select actions.
    - env (gym.Env): The Shooter environment instance to interact with.
    - device (torch.device): The device (CPU or GPU) on which to run the model.

    Returns:
    - float: The total accumulated reward from the episode.
    '''

    # We need pygame so that we can handle keyboard events and, at the end of
    # the episode, close the display window. The keyboard is *not* to interact
    # with the game, but we might want to close early.
    config = config or load_config()
    clock = pygame.time.Clock()
    env = ShooterEnv(render_mode="human", max_episode_steps=config.training.max_steps,
                     reward_settings=config.reward)
    if not pygame.get_init():
        pygame.init()
        pygame.mixer.init()

    if model is None:
        obs_size = env.observation_space.shape[0]
        n_actions = env.action_space.n
        model = DQN(obs_size, n_actions)

    # Take the model out of training mode
    model.to(device)
    model.eval()

    # Initialize this episode and setup the 'state' to be a tensor since our
    # DQN model is expecting all inputs to be tensors.
    state, info = env.reset(seed=config.training.seed)
    state = torch.from_numpy(state).unsqueeze(0).float().to(device)
    total_reward = 0
    done = False

    # Loop until this episode is complete.
    while not done:

        # Allow user to quit early.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print(f">> Window closed. Ending visualization early. <<\n")
                done = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                print(f">> Escape pressed. Ending visualization early. <<\n")
                done = True

        # Display the current frame
        env.render()

        # Choose the next best thing (being careful not to accidentally train).
        with torch.no_grad():
            q_vals = model(state)
            action = q_vals.argmax().item()

        # Perform the next action in the environment.
        next_state, reward, terminated, truncated, info = env.step(action)
        done = done or terminated or truncated
        total_reward += reward
        state = torch.from_numpy(next_state).unsqueeze(0).float().to(device)
        clock.tick(FPS)

    # Gracefuly close PyGame environment and return.
    time.sleep(1)
    env.close()
    return total_reward


def main(model_path, config=None):
    config = config or load_config()
    device = torch.device(config.training.device)
    model = DQN(9, 7)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    return visualize_episode(model, device, config)


def cli():
    parser = argparse.ArgumentParser(description='Play a weights checkpoint using an experiment config')
    parser.add_argument('model_path')
    parser.add_argument('--config')
    args = parser.parse_args()
    try:
        reward = main(args.model_path, load_config(args.config))
        print(f'Episode finished with {reward} reward')
    finally:
        pygame.quit()


if __name__ == '__main__':
    cli()
