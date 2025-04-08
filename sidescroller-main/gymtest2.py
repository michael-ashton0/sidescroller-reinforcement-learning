import gymenv
import gymnasium as gym
from gymenv import ShooterEnv

# Create and initialize gym environment WITH RENDERING
env = gym.make('Shooter-v0', render_mode='human')
obs, info = env.reset()
print(f"Initial observation shape: {obs.shape}")
print(f"Initial debug info:\n{info}\n")

# Initialize training variables
done = False
total_reward = 0
step_count = 0

# Pretty debug strings; not required for testing.
action_list = [ 'Run Right', 'Run Left', 'Jump', 
               'Jump Left', 'Jump Right', 'Shoot', 'Grenade' ]

# Verify 1 episode with 500 training steps without crashing
while not done and step_count < 1000:
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    env.render() # Does nothing since we initialized render_mode=None
    total_reward += reward
    step_count += 1
    action = action_list[action]

    print(f"Step {step_count:5}: action={action:<10} "
          f"reward={reward:>6.2f} "
          f"health={info['player_health']:2} "
          '''f"position=({info['player_distance'][0]:4}, {info['player_distance'][0]:4}) "
          f"exit=({info['exit_distance'][0]:4}, {info['exit_distance'][0]:4})"'''
          f"done={terminated or truncated}")

print(f"Total reward after {step_count} steps: {total_reward:.2f}")
env.close()