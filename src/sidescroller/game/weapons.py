from sidescroller.assets import asset_path

import pygame
from pygame.time import get_ticks
from pygame.image import load
from sidescroller.settings import ENVIRONMENT, TILEMAP
from os import listdir


class ItemBox(pygame.sprite.Sprite):
    '''
    Supplies for the player to collect with ammo, grenades, or health.
    '''
    images = None

    @classmethod
    def load_assets(cls):
        '''
        Preload assets into shared memory to optimize performance.
        '''
        cls.images = {
            'ammo': load(asset_path(f'img/icons/ammo_box.png')).convert_alpha(),
            'health': load(asset_path(f'img/icons/health_box.png')).convert_alpha(),
            'grenade': load(asset_path(f'img/icons/grenade_box.png')).convert_alpha(),
        }

    def __init__(self, x, y, box_type='ammo', quantity=20):
        '''
        Initializes an ItemBox based on the box type
        '''
        super().__init__()
        if not ItemBox.images:
            ItemBox.load_assets()

        self.box_type = box_type
        self.quantity = quantity
        self.image = ItemBox.images[box_type]
        self.rect = self.image.get_rect()
        self.rect.midtop = (x, y - self.image.get_height())

    def draw(self, screen, camera_x):
        '''
        Draws this Item box after setting the camera position.
        '''        
        screen.blit(self.image, (self.rect.x + camera_x, self.rect.y))


class Bullet(pygame.sprite.Sprite):
    '''
    Bullets for the Soldier to shoot.
    '''
    image = None

    @classmethod
    def load_assets(cls):
        '''
        Preload assets into shared memory to optimize performance.
        '''
        # Load media from disk into shared memory for each instance to copy
        cls.image = pygame.image.load(asset_path('img/icons/bullet.png')).convert_alpha()

        # Bullets eventually go off the end of the level
        cls.remove_at_x = TILEMAP.COLS * TILEMAP.TILE_SIZE

    def __init__(self, x, y, direction):
        '''
        Initialize Bullet object; a weapon Soldiers shoot.
        '''                
        super().__init__()
        if not Bullet.image:
            Bullet.load_assets()

        self.vel_x = ENVIRONMENT.BULLET_VELOCITY_X
        self.damage = ENVIRONMENT.BULLET_FULL_DAMAGE
        self.direction = direction
        self.image = Bullet.image
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        #Bullet.sound_fx.play() moved to Game Engine

    def update(self):
        '''
        Updates the position of the bullet. Most other objects are controlled
        by the physics engine. But since bullets are not affected by gravity
        (we treat them more like lasers), we need a special handler here.
        '''
        self.rect.x += self.vel_x * self.direction
        if self.rect.right < 0 or self.rect.left > Bullet.remove_at_x:
            self.kill()        

    def draw(self, screen, camera_x):
        '''
        Draws this Item box after setting the camera position.
        '''                
        screen.blit(self.image, (self.rect.x + camera_x, self.rect.y))


class Grenade(pygame.sprite.Sprite):
    '''
    A weapon for Soldier objects to throw that cause splash damage.
    '''
    image = None

    @classmethod
    def load_assets(cls):
        '''
        Preload assets into shared memory to optimize performance.
        '''
        cls.image = pygame.image.load(asset_path('img/icons/grenade.png')).convert_alpha()

    def __init__(self, x, y, direction, time_based_fuse=False):
        '''
        Initialize Grenade object; a weapon thrown by soldiers.
        '''        
        super().__init__()
        if not Grenade.image:
            Grenade.load_assets()

        self.in_air = True
        self.vel_x = ENVIRONMENT.GRENADE_VELOCITY_X
        self.vel_y = ENVIRONMENT.GRENADE_VELOCITY_Y
        self.inner_radius = ENVIRONMENT.GRENADE_INNER_RADIUS
        self.outer_radius = ENVIRONMENT.GRENADE_OUTER_RADIUS
        self.full_damage = ENVIRONMENT.GRENADE_FULL_DAMAGE
        self.image = Grenade.image
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction
        self.time_based_fuse = time_based_fuse
        if self.time_based_fuse:
            self.throw_time = get_ticks()
        else: # frame based animations for RL environments
            self.throw_time = 0
        self.do_explosion = False

    def damage_at(self, pos_rect):
        '''
        Determine the amount of splash damage at a particular point. We use
        Manhattan Distance instead of Euclidean Distance because there is no
        square root calculation (which is slow).
        '''
        damage = 0
        manhattan_dist = (abs(self.rect.centerx - pos_rect.centerx) +
                          abs(self.rect.centery - pos_rect.centery))
        if manhattan_dist > self.outer_radius:
            damage = 0
        elif manhattan_dist < self.inner_radius:
            damage = self.full_damage
        else:
            # y = A * (1 - x / B)
            A = self.full_damage
            B = self.outer_radius - self.inner_radius
            damage = int(A * (1 - (manhattan_dist - self.inner_radius) / B))
        return damage
    
    def landed(self, impact_velocity):
        '''
        The physics engine calls this function when a Grenade hits the ground.
        It stops the object from moving further at its original velocity.
        '''
        self.vel_y = 0
        self.vel_x = 0
        self.in_air = False

    def update(self):
        '''
        Determines when the grade should explode.
        '''
        if self.time_based_fuse:
            if get_ticks() >= self.throw_time + ENVIRONMENT.GRENADE_FUSE_TIME:
                self.do_explosion = True
        else: # frame based animations for RL environments
            self.throw_time += 1
            if self.throw_time >= ENVIRONMENT.GRENADE_COOLDOWN:
                self.do_explosion = True

    def draw(self, screen, camera_x):
        '''
        Draws this Item box after setting the camera position.
        '''                
        screen.blit(self.image, (self.rect.x + camera_x, self.rect.y))


class Explosion(pygame.sprite.Sprite):
    '''
    Animation sequence object for an exploding grenade.
    '''
    animations = None

    @classmethod
    def load_assets(cls):
        '''
        Preload assets into shared memory to optimize performance.
        '''
        cls.animations = []
        num_of_frames = len(listdir(asset_path(f'img/explosion')))
        for i in range(num_of_frames):
            img = pygame.image.load(asset_path(f'img/explosion/exp{i}.png'))
            new_width = int(img.get_width() * 2)
            new_height = int(img.get_height() * 2)
            img = pygame.transform.scale(img, (new_width, new_height))
            cls.animations.append(img.convert_alpha())

    def __init__(self, x, y, time_based_fuse=False):
        '''
        Initialize Explosion object; an animation sequence for grenades.
        '''
        super().__init__()
        if not Explosion.animations:
            Explosion.load_assets()

        self.frame_idx = 0
        self.counter = 0
        self.animations = Explosion.animations
        self.image = self.animations[self.frame_idx]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.time_based_fuse = time_based_fuse
        if self.time_based_fuse:
            self.animation_time = get_ticks()
        else: # frame based animations for RL environments
            self.animation_time = 0
        #Explosion.sound_fx.play() # Moved to Game Engine

    def _advance_frame(self):
        '''
        Helper function to advance the explosion animation by one frame. The
        responsibility for timing the animation is elsewhere.
        '''
        self.frame_idx += 1
        if self.frame_idx >= len(self.animations):
            self.kill()
        else:
            self.image = self.animations[self.frame_idx]

    def update(self):
        '''
        Updates the explosion animation sequence.
        '''
        if self.time_based_fuse:
            if get_ticks() >= self.animation_time + ENVIRONMENT.ANIMATION_DELAY:
                self.animation_time = get_ticks()
                self._advance_frame()
        else: # frame based animations for RL environments
            self.animation_time += 1
            if self.animation_time >= ENVIRONMENT.ANIMATION_COOLDOWN:
                self.animation_time = 0
                self._advance_frame()

    def draw(self, screen, camera_x):
        '''
        Draws this Item box after setting the camera position.
        '''                
        screen.blit(self.image, (self.rect.x + camera_x, self.rect.y))

