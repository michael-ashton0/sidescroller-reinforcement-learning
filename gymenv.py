import os
import random
import pygame
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from gymnasium.envs.registration import register
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILEMAP, DEFAULT_EPISODE_STEPS, RewardSettings
from engine import GameEngine, TextBar
from controller import GameController

# Not required unless we want to provide traditional gym.make capabilities
register(id='Shooter-v0',
         entry_point='gymenv:ShooterEnv',
         max_episode_steps=DEFAULT_EPISODE_STEPS,
         kwargs={'max_episode_steps': None})

class ShooterEnv(gym.Env):
    '''
    Wrapper class that creates a gym interface to the original game engine.
    '''

    # Hints for registered environments; ignored otherwise
    metadata = {
        'render_modes': ['human'],
        'render_fps': 60
    }

    def __init__(self, render_mode=None, max_episode_steps=DEFAULT_EPISODE_STEPS,
                 reward_settings=None):
        '''
        Initializes a new Gymnasium environment for the Shooter Game. Loads the
        game engine into the background and defines the action space and the
        observation space.
        '''

        super().__init__()
        if render_mode not in (None, 'human'):
            raise ValueError(f'Unsupported render mode: {render_mode}')
        if max_episode_steps is not None and max_episode_steps <= 0:
            raise ValueError('max_episode_steps must be positive')
        self.reward_settings = reward_settings if reward_settings is not None else RewardSettings()
        self._closed = False
        self.render_mode = render_mode
        self.max_episode_steps = max_episode_steps
        if render_mode is None and not pygame.display.get_init():
            os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.font.get_init():
            # Font objects cannot survive pygame.font.quit()/pygame.quit().
            TextBar.font = None
        pygame.font.init()
        if render_mode == 'human':
            pygame.mixer.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
            self.screen = None
        self.game = GameEngine(self.screen)
        self._ended = True
        # Discrete action space: 7 possible moves
        self.action_space = spaces.Discrete(7)
        '''
        + x_distance from goal (do we really need y distance?)
        + death (I think this removes the need to keep track of health unless I want a bot that doesn't take damage)
        + finish level
        + time taken (if I want fast over 'perfect')
        + num_bullets
        + num_nades
        '''
        # Observation format: [exit_dx, exit_dy, start_dx, start_dy, alive, finished, front_right_tile]
        low = np.array([-100000, -100000, -100000, -100000, 0, 0, 0, 0, 0])
        high = np.array([100000, 100000, 100000, 100000, 1, 1, 20, 20, 1])
        self.observation_space = spaces.Box(low, high, dtype=np.float32)

        ## ORIGINAL ##
        # Observation: [dx, dy, health, exit_dx, exit_dy, ammo, grenades]
        '''
        low = np.array([-10000, -1000, 0, -10000, -10000, 0, 0], dtype=np.float32)
        high = np.array([10000, 1000, 100, 10000, 10000, 50, 20], dtype=np.float32)
        self.observation_space = spaces.Box(low, high, dtype=np.float32)
        '''


    def reset(self, seed=None, options=None):
        '''
        Resets the game environment for the beginning of another episode.
        '''
        if self._closed:
            raise RuntimeError("Cannot reset a closed environment; create a new instance")
        super().reset(seed=seed)
        if seed is not None:
            self.action_space.seed(seed)
        self.game.rng = random.Random(int(self.np_random.integers(2**32)))
        self._ended = False
        self.step_count = 0
        self.game.reset_world()
        self.game.load_current_level()

        # Tracks observation and reward values across steps
        self.start_x = self.game.player.rect.centerx
        self.start_y = self.game.player.rect.centery
        self.previous_x = self.start_x

        # Initialize the variables I decided were important for debugging
        debug_info = {
            'player_health': self.game.player.health,
            'player_distance': (0, 0),
            'exit_distance': self._get_exit_offset(self.game.player)
        }

        # Return the initial game state
        observation, debug_info = self._get_observation()
        return observation, debug_info


    def step(self, action):
        '''
        Agent performs a single action in the game environemnt.
        '''
        if self._ended:
            raise RuntimeError('Call reset before stepping a new episode')
        if not self.action_space.contains(action):
            raise ValueError(f'Invalid action: {action}')
        self.last_action = int(action)
        controller = self._action_to_controller(action)
        self.game.update(controller)
        self.step_count += 1

        observation, debug_info = self._get_observation()
        reward = self._get_reward()
        terminated = not self.game.player.alive or self.game.level_complete
        truncated = (self.max_episode_steps is not None
                     and self.step_count >= self.max_episode_steps and not terminated)
        self._ended = terminated or truncated

        return observation, reward, terminated, truncated, debug_info


    def render(self):
        ''' 
        Visually renders the game so that viewers can watch the agent play. The
        first time this function is called, it initializes the PyGame display
        and mixer (just like a real game). If the self. Every time that it is called, this
        function draws the game.
        '''
        # Do nothing if rendering is disabled
        if self.render_mode != "human":
            return
        screen = pygame.display.get_surface()
        # Draw the screen        
        self.game.draw()
        pygame.display.update()

    def is_moving(self, p):
        p = self.game.player
        if p.vel_x == 0 and p.vel_y == 0:
          return False
        else:
           return True

        
    def _get_observation(self):
        p = self.game.player

        # Distance from start
        start_dx = p.rect.centerx - self.start_x
        start_dy = p.rect.centery - self.start_y
        
        # Exit distance
        exit_dx, exit_dy = self._get_exit_offset(p)

        # Check if the player is moving
        moving = self.is_moving(p) 
             
        alive = self.game.player.alive 
        finished = self.game.level_complete
        
        # Query the loaded world; positions are world coordinates, independent of camera.
        tile_x = p.rect.centerx // TILEMAP.TILE_SIZE + 1
        tile_y = p.rect.centery // TILEMAP.TILE_SIZE
        def hazard(row, col):
            data = self.game.world_data
            if not (0 <= row < len(data) and 0 <= col < len(data[row])):
                return 0
            return int(TILEMAP.WATER_TILE_FIRST <= data[row][col] <= TILEMAP.WATER_TILE_LAST)
        front_right_tile = hazard(tile_y, tile_x) if not p.in_air else 1
        front_bottom_tile = hazard(tile_y + 1, tile_x) if not p.in_air else 1

        # Create an observation (4 values)
        obs = [
            exit_dx,
            exit_dy,
            start_dx,
            start_dy,
            alive,
            finished,
            front_right_tile,
            front_bottom_tile,
            moving
        ]

        # Create debug information
        debug_info = {
            'player_health': p.health,
            'player_distance': (start_dx, start_dy),
            'exit_xdistance': (exit_dx),
        }

        return np.array(obs, dtype=np.float32), debug_info
    

    def _get_exit_offset(self, player):
        min_dist = float('inf')
        closest_dx, closest_dy = 9999, 9999

        for tile in self.game.groups['exit']:
            dx = tile.rect.centerx - player.rect.centerx
            dy = tile.rect.centery - player.rect.centery
            dist = abs(dx) + abs(dy)
            if dist < min_dist:
                min_dist = dist
                closest_dx = dx
                closest_dy = dy
        return closest_dx, closest_dy


    def _get_reward(self):
        p = self.game.player
        progress = p.rect.centerx - self.previous_x
        self.previous_x = p.rect.centerx
        if not p.alive:
            return float(self.reward_settings.death)
        reward = self.reward_settings.progress * progress
        # Actions are controller commands; animation enums never represent shooting.
        if self.last_action == 5:
            reward += self.reward_settings.shoot
        elif self.last_action == 6:
            reward += self.reward_settings.throw
        if self.game.level_complete:
            reward += self.reward_settings.completion
        return float(reward)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._ended = True
        if self.render_mode == 'human' and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        pygame.display.quit()

    def _action_to_controller(self, action):
        '''
        Converts an action (just an integer) to a game controller object.
        '''
        # Do you have to come to a full stop to shoot or throw a grenade?
        # Understand the simplicity since too many controls is hard to teach
        ctrl = GameController()
        if action == 0: ctrl.mleft = True
        elif action == 1: ctrl.mright = True
        elif action == 2: ctrl.jump = True
        elif action == 3: ctrl.jump = ctrl.mleft = True
        elif action == 4: ctrl.jump = ctrl.mright = True
        elif action == 5: ctrl.shoot = True
        elif action == 6: ctrl.throw = True
        return ctrl
