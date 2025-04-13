import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR, TILEMAP
pygame.init()
pygame.mixer.init()
pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Shooter')
from os import environ
import numpy as np
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
import gymnasium as gym
from gymnasium import spaces
from gymnasium.envs.registration import register
from engine import GameEngine
from controller import GameController
import csv

# Not required unless we want to provide traditional gym.make capabilities
register(id='Shooter-v0',
         entry_point='gymenv:ShooterEnv',
         max_episode_steps=5000)

class ShooterEnv(gym.Env):
    '''
    Wrapper class that creates a gym interface to the original game engine.
    '''

    # Hints for registered environments; ignored otherwise
    metadata = {
        'render_modes': ['human'],
        'render_fps': 60
    }

    def __init__(self, render_mode=None):
        '''
        Initializes a new Gymnasium environment for the Shooter Game. Loads the
        game engine into the background and defines the action space and the
        observation space.
        '''

        super().__init__()
        self.render_mode = render_mode
        pygame.init()
        pygame.display.init()
        if self.render_mode != 'human':
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
        else:
            pygame.init()
            pygame.mixer.init()
            pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption('Shooter')

        self.screen = pygame.display.get_surface()
        self.game = GameEngine(self.screen)
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
        # Observation format: [exit_dx, exit_dy, alive, finished, self.step_count, p.ammo, front_right_tile]
        low = np.array([-100000, -100000, 0, 0, 0, 0, 0, 0])
        high = np.array([100000, 100000, 1, 1, 2000, 50, 20, 20])
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
        self.step_count = 0
        self.game.reset_world()
        self.game.load_current_level()

        # Tracks observation and reward values across steps
        self.start_x = self.game.player.rect.centerx
        self.start_y = self.game.player.rect.centery

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
        controller = self._action_to_controller(action)
        self.game.update(controller)
        self.step_count += 1

        observation, debug_info = self._get_observation()
        reward = self._get_reward()
        terminated = not self.game.player.alive or self.game.level_complete
        truncated = self.step_count >= 1000

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


    def _get_observation(self):
        p = self.game.player
    
        # Distance from start
        p_dx = p.rect.centerx - self.start_x
        p_dy = p.rect.centery - self.start_y
        
        # My observations
        # Exit distance
        exit_dx, exit_dy = self._get_exit_offset(p)
        # Do we need to check alive and finished since they are already calculated in rewards?
             
        alive = self.game.player.alive 

        finished = self.game.level_complete

        '''
        + x_distance from goal (do we really need y distance?)
        + death (I think this removes the need to keep track of health unless I want a bot that doesn't take damage)
        + finish level
        + step_count
        + num_bullets
        + num_nades
        '''

        # Check if there is ground in front of the player
        def get_front_right_tile(p):
            self.world_data = []
            with open(f'level{self.game.level}_data.csv', 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                for idx_y, row_of_tiles in enumerate(reader):
                    self.world_data.append([])
                    for idx_x, tile_data in enumerate(row_of_tiles):
                        self.world_data[idx_y].append(int(tile_data))
            tile_x = p.rect.centerx // 45
            tile_y = p.rect.centery // 45
            tile_ahead_x = tile_x + 1
            tile_below_y = tile_y + 1
            tile_ahead = self.world_data[tile_y][tile_ahead_x]
            tile_below = self.world_data[tile_below_y][tile_ahead_x]
            # Check if the tile is a solid tile (1-20) or empty (-1)
            if tile_ahead in [7,8,9, -1]: # water tile or empty space
                tile_ahead = 1 if tile_ahead in range(1, 21) else 0
            else:
                tile_ahead = 0
            if tile_below in [7,8,9, -1]:
                tile_below = 1 if tile_below in range(1, 21) else 0
            else:
                tile_below = 0

            return tile_ahead, tile_below
        
        front_right_tile = get_front_right_tile(p)[0]
        front_bottom_tile = get_front_right_tile(p)[1]


        # Create an observation (4 values)
        obs = [
            exit_dx,
            exit_dy,
            alive,
            finished,
            self.step_count,
            p.ammo,
            front_right_tile,
            front_bottom_tile
        ]

        # Create debug information
        debug_info = {
            'player_health': p.health,
            'player_distance': (p_dx, p_dy),
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
        # TODO: Balance the death and rewards so that getting far and dying gives a higher reward than staying at the start
        if not self.game.player.alive:
            return -100_000_000
         # Originally was reward increment as player increases distance from start
         # Decided that minimizing distance from the end was my approach
         # I'm thinking that this also incentivizes taking a long time but I am not sure
        reward = 10 * (self._get_exit_offset(self.game.player)[0] - self.game.player.rect.centerx)
        reward += 10 * (self._get_exit_offset(self.game.player)[1] - self.game.player.rect.centery)
        #reward -= (1 * self.step_count)
        if self.game.player.action == 'jump' and not self.game.player.in_air:
            reward += 10_000
        if self.game.player.action == 'shoot' or 'throw':
            reward -= 1_000_000
        
        if self.game.level_complete:
            reward += 100_000_000
        
        return reward


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