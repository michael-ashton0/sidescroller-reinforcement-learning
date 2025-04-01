import os
import random
import pygame
from pygame.time import get_ticks
from weapons import Bullet, Grenade
from settings import Direction, Action, ENVIRONMENT, TILEMAP


# All soldiers share these common animation types
animation_types = ['Idle', 'Run', 'Jump', 'Death']

class Soldier(pygame.sprite.Sprite):
    '''
    Base class for a soldier object that can be used for all human sprites.
    '''

    animations = {}
    jump_fx = None

    @classmethod
    def load_assets(cls, base_dirpath, soldier_type):
        '''
        Preload animations and sounds into shared memory for reuse.
        '''
        if soldier_type not in cls.animations:
            cls.animations[soldier_type] = cls._load_animations(base_dirpath)
            
        if cls.jump_fx is None:
            cls.jump_fx = pygame.mixer.Sound('audio/jump.wav')
            cls.jump_fx.set_volume(0.5)

    @staticmethod
    def _load_animations(base_dirpath):
        '''
        Generates an ordered list of animation frames containing every image 
        within a file directory. There are four different animation types, each
        in an appropriately named subdirectory: 'Idle', 'Run', 'Jump', and
        'Death'. The images must be named 1.png, 2.png, 3.png, etc. There is no
        restriction on the number of images in the animation sequence.
        '''

        animation_images = []
        for action in animation_types:
            action_dir = f'{base_dirpath}/{action}'
            image_list = []
            frame_count = len(os.listdir(action_dir))
            for i in range(frame_count):
                img = pygame.image.load(f'{action_dir}/{i}.png')
                scaled_width = int(img.get_width() * ENVIRONMENT.SOLDIER_SCALE)
                scaled_height = int(img.get_height() * ENVIRONMENT.SOLDIER_SCALE)
                img = img.convert_alpha()
                img = pygame.transform.scale(img, (scaled_width, scaled_height))
                image_list.append(img)
            animation_images.append(image_list)
        return animation_images
    

    def __init__(self, x, y, kind, speed=3, health=100, ammo=20, grenades=5):
        '''
        Initializes a Soldier object by setting all the default values.
        '''        
        super().__init__()
        Soldier.load_assets(f'img/{kind}', kind)

        self.alive = True
        self.health = health
        self.speed = speed
        self.ammo = ammo
        self.grenades = grenades
        self.max_ammo = ammo * 2
        self.max_grenades = grenades * 2
        self.max_health = health
        self.direction = Direction.RIGHT
        self.vel_y = 0
        self.vel_x = 0
        self.in_air = True
        self.jump = False

        # Action/Animation sprite related variables
        self.frame_idx = 0
        self.action = Action.IDLE
        self.animations = Soldier.animations
        self.image = self.animations[kind][self.action][self.frame_idx]
        self.rect = self.image.get_rect()
        self.animation_time = get_ticks()
        self.shoot_time = self.animation_time
        self.throw_time = self.animation_time
        self.shoot_delay = ENVIRONMENT.SOLDIER_SHOOT_DELAY
        self.throw_delay = ENVIRONMENT.SOLDIER_THROW_DELAY

        # Adjusts the rectangle to be slightly smaller than image so that the
        # player falls through tile gaps; otherwise the player float on air
        self.rect.x += 3
        self.rect.y -= 1
        self.rect.width -= 6
        self.rect.height -= 2
        self.rect.center = (x, y)

    def update(self):
        '''
        Updates the soldier's internal variables with each iteration through
        the game loop. Mostly used for animation sequences.
        '''

        # Handle player animations
        new_action = (Action.JUMP if self.in_air 
                      else Action.RUN if self.vel_x != 0 
                      else Action.DEATH if not self.alive
                      else Action.IDLE)
        if new_action != self.action:
            self.animation_time = get_ticks()
            self.action = new_action
            self.frame_idx = 0

        # Update timed sequences like animation frames
        if get_ticks() > self.animation_time + ENVIRONMENT.ANIMATION_DELAY:
            self.animation_time = get_ticks()
            self.frame_idx += 1
            # Animation rollover (except for the death sequence)
            if self.frame_idx >= len(self.animations[self.action]):
                if self.action == Action.DEATH:
                  self.frame_idx = len(self.animations[self.action]) - 1
                else:
                    self.frame_idx = 0
        
        # Update the animation frame
        self.image = self.animations[self.action][self.frame_idx]

        # Nothing particularly interesting to return
        return None

    def move(self, mleft_cmd, mright_cmd, jump_cmd):
        '''
        Initiates jumping and lateral movements from the Soldier by setting
        initial velocities. It is a response to input from buttons on the
        controller. The physics engine is responsible for tracking/updating
        the position and velocity of the Soldier over time.
        '''

        # Handle vertical movement
        if jump_cmd and not self.in_air and self.vel_y == 0:
            Soldier.jump_fx.play()
            self.vel_y = ENVIRONMENT.SOLDIER_JUMP_STRENGTH
            self.in_air = True
            if not mright_cmd:
                vector = 'left'
            else:
                vector = 'right'

        # Handle lateral movement
        if mleft_cmd and not mright_cmd:
            self.direction = Direction.LEFT
            if self.in_air:
                self.vel_x += self.speed / 15
            else:
                self.vel_x = self.speed
        elif mright_cmd and not mleft_cmd:
            self.direction = Direction.RIGHT
            if self.in_air:
                self.vel_x += self.speed / 15
            else:
                self.vel_x = self.speed
        else:
            # holding both buttons simultaneously
            self.vel_x = 0

    def landed(self, impact_velocity):
        '''
        The physics engine calls this function when the Soldier is jumping and
        hits the ground. It records the fact that the soldier can jump again.
        '''
        if self.vel_y > 19:
            self.health -= (self.vel_y - 13)
        self.vel_y = 0
        self.in_air = False

    def shoot(self):
        '''
        Shoots a bullet if the Soldier has one. This function calculates the 
        physical xy-location bullet and its direction of travel. The physics
        engine is responsible for calculating its movements.

        It's important that the bullet starts outside of the Soldier's rect
        or the game engine will detect it as a suicide shot.
        '''

        if (self.ammo > 0 
                and get_ticks() > self.shoot_time + self.shoot_delay):
            self.ammo -= 1
            self.shoot_time = get_ticks()
            x = self.rect.centerx + (30 * self.direction) # 30 is hack
            y = self.rect.centery
            return Bullet(x, y, self.direction)
        else:
            return None

    def throw(self):
        '''
        Throws a grenade if the Soldier has one. This function calculates the 
        physical xy-location grenade and its direction of travel. The physics
        engine is responsible for calculating its movements.
        '''
        if (self.grenades > 0 
                and get_ticks() > self.throw_time + self.throw_delay):
            self.grenades -= 1
            self.throw_time = get_ticks()
            x_offset = int(self.rect.size[0] * 0.2 * self.direction.value)
            x = self.rect.centerx + x_offset
            y = self.rect.top
            return Grenade(x, y, self.direction)
        else:
            return None

    def death(self):
        '''
        Kills this Soldier by updating the animation and clearing variables.
        '''
        self.health = 0
        self.vel_x = 0
        self.alive = False

    def draw(self, screen, camera_x):
        '''
        Draws this Soldier after flipping and setting camera position.
        '''
        flip_imgx = True if self.direction == Direction.LEFT else False
        img = pygame.transform.flip(self.image, flip_imgx, False)
        screen.blit(img, (self.rect.x + camera_x, self.rect.y))


class Enemy(Soldier):

    def __init__(self, x, y, speed=2, health=100, ammo=20, grenades=5):
        '''
        Initializes an Enemy object by setting animation frames and delays.
        '''        
        super().__init__(x, y, 'enemy', speed, health, ammo, grenades)
        self.animations = Soldier.animations['enemy']

        self.move_counter = 0
        self.vision = pygame.Rect(x, y, 450, 5)
        self.idling = False
        self.idling_counter = 0

    def ai_move(self, world_map, tile_size, movement_limit=200):
        '''
        AI movement, ensuring enemies don't walk into walls or off cliffs.
        '''
       
        # If enemy is idling, stop moving
        if self.idling:
            self.vel_x = 0
            self.idling_counter -= 1
            if self.idling_counter <= 0:
                self.idling = False
                self.move_counter = 0
            return

        # Calculate tiles in front of enemy position
        tile_x = self.rect.centerx // tile_size
        tile_y = self.rect.centery // tile_size
        tile_ahead_x = tile_x + self.direction
        tile_below_y = tile_y + 1
        tile_ahead = world_map[tile_y][tile_ahead_x]
        tile_below = world_map[tile_below_y][tile_ahead_x]

        # Check for walls, cliffs, and random behavior
        wall_ahead = False
        cliff_ahead = False
        random_turn = False
        if (tile_ahead >= TILEMAP.DIRT_TILE_FIRST and
                tile_ahead <= TILEMAP.DIRT_TILE_LAST):
            wall_ahead = True
        elif (tile_below == TILEMAP.EMPTY_TILE or
                (tile_below >= TILEMAP.WATER_TILE_FIRST
                 and tile_below <= TILEMAP.WATER_TILE_LAST)):
            cliff_ahead = True
        elif random.randint(1, movement_limit) == 1:
            random_turn = True

        # Reasons to turn and pause
        if (wall_ahead or cliff_ahead or random_turn 
                or self.move_counter >= movement_limit):
            self.direction *= -1
            self.idling = True
            self.move_counter = 0
            self.idling_counter = random.randint(25, 75)                
        
        # Otherwise, move forward
        else:
            ai_moving_right = self.direction == Direction.RIGHT
            ai_moving_left = not ai_moving_right
            super().move(ai_moving_left, ai_moving_right, False)
            self.move_counter += 1

    def update(self):
        '''
        Updates the Enemy by turning head to match the direction he's facing.
        '''
        super().update()
        self.vision.top = self.rect.top
        if self.direction == Direction.LEFT:
            self.vision.right = self.rect.left
        else:
            self.vision.left = self.rect.right


class Player(Soldier):
    '''
    This class creates the main character in the game. Usually, this means an
    interactive human player but it's also possible for the character to be
    controlled by a special AI agent.
    '''

    def __init__(self, x, y, speed=5, health=100, ammo=20, grenades=5):
        '''
        Initializes a Player object by setting animation frames and delays.
        '''
        super().__init__(x, y, 'player', speed, health, ammo, grenades)
        self.animations = Soldier.animations['player']
        self.shoot_delay = ENVIRONMENT.PLAYER_SHOOT_DELAY
        self.throw_delay = ENVIRONMENT.PLAYER_THROW_DELAY
