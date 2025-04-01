
import csv
import pygame
from pygame.sprite import spritecollide
from pygame.transform import scale
from pygame.sprite import Group
from pygame.image import load
from pygame.draw import rect
from os.path import exists
from soldier import Player, Enemy
from weapons import ItemBox, Explosion
from settings import (SCREEN_HEIGHT, SCREEN_WIDTH, SCROLL_RIGHT, SCROLL_LEFT,
                      ENVIRONMENT, TILEMAP, COLOR, Direction, GameModes)


class GameEngine():
    '''
    An engine to play the CSC432 side-scrolling shooter game. This class is
    the most complicated in the game because it incldes a physics engine, 
    tracks all of the individual sprites, determines hit damage, etc. etc.
    Very few, if any, of the functions return values. Instead, they all modify
    internal state variables.
    '''

    # Load the background images (order matters)
    bg_img = None
    bg_ypos = None
    bg_width = 0
    tile_img_list = None

    @classmethod
    def load_assets(cls, headless):
        '''
        Preload sounds and background images into shared memory for reuse.
        '''
        # Intialize background music
        if not headless:
            pygame.mixer.music.load('audio/music.mp3')
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1, 0.0, 2500)

        # Load all of the background images
        if cls.bg_img is None:
            cls.bg_img = [
                load('img/background/sky_cloud.png').convert_alpha(),
                load('img/background/mountain.png').convert_alpha(),
                load('img/background/pine1.png').convert_alpha(),
                load('img/background/pine2.png').convert_alpha()
            ]
            cls.bg_width = min([img.get_width() for img in cls.bg_img])
        if cls.bg_ypos is None:
            cls.bg_ypos = [
                0,
                SCREEN_HEIGHT - cls.bg_img[1].get_height() - 200,
                SCREEN_HEIGHT - cls.bg_img[2].get_height() - 150,
                SCREEN_HEIGHT - cls.bg_img[3].get_height()
            ]
        
        # Load all possible foreground tiles
        if cls.tile_img_list is None:
            cls.tile_img_list = []
            for tile_num in range(TILEMAP.TILE_TYPE_COUNT):
                img = load(f'img/tile/{tile_num}.png').convert_alpha()
                img = scale(img, (TILEMAP.TILE_SIZE, TILEMAP.TILE_SIZE))
                cls.tile_img_list.append(img)


    def __init__(self, screen=None, game_mode=GameModes.MENU):
        '''
        Creates a new world object.
        '''
        self.game_mode = game_mode
        self.level = 1
        self.screen = screen
        GameEngine.load_assets(True if screen is None else False)


    def reset_world(self):
        ''' 
        Resets the sprites and camera for a new level
        '''
        self.player = None
        self.health_bar = None
        self.level_complete = False
        self.camera_scroll = 0
        self.bg_scroll = 0

        # Create a bunch of empty sprite groups
        self.group_names = [ 'obstacle', 'water', 'decoration', 'exit', 'item',
                             'enemy', 'bullet', 'grenade', 'explosion' ]
        self.groups = { group:Group() for group in self.group_names }


    def load_game_tile(self, tile, idx_x, idx_y):
        '''
        Loads an individual game tile by creating the tile object and adding
        it to the appropriate sprite group.
        '''

        # Take an image from the preloaded game tiles
        img = GameEngine.tile_img_list[tile]
        rect = img.get_rect()
        rect.x = idx_x * TILEMAP.TILE_SIZE
        rect.y = idx_y * TILEMAP.TILE_SIZE

        # Create internal object to represent this tile and add to group
        # MUST MAINTAIN RELATIVE ORDER OF THIS SEQUENCE OF IF-STATEMENTS
        if tile <= TILEMAP.DIRT_TILE_LAST:
            obstacle_tile = GameTile(img, rect.x, rect.y)
            self.groups['obstacle'].add(obstacle_tile)
        elif tile <= TILEMAP.WATER_TILE_LAST:
            water_tile = GameTile(img, rect.x, rect.y)
            self.groups['water'].add(water_tile)
        elif tile <= TILEMAP.DECORATION_TILE_LAST:
            decoration_tile = GameTile(img, rect.x, rect.y)
            self.groups['decoration'].add(decoration_tile)
        
        # Only one ID per tile, so order doesn't matter so much
        elif tile == TILEMAP.PLAYER_TILE_ID:
            self.player = Player(rect.x, rect.y)
            self.health_bar = HealthBar(10, 10, self.player.max_health)
            self.ammo_bar = TextBar(10, 35, COLOR.WHITE)
            self.grenade_bar = TextBar(10, 60, COLOR.WHITE)
        elif tile == TILEMAP.ENEMY_TILE_ID:
            enemy = Enemy(rect.x, rect.y)
            self.groups['enemy'].add(enemy)
        elif tile == TILEMAP.AMMO_TILE_ID:
            item = ItemBox(rect.x, rect.y, 'ammo')
            self.groups['item'].add(item)
        elif tile == TILEMAP.GRENADE_TILE_ID:
            item = ItemBox(rect.x, rect.y, 'grenade')
            self.groups['item'].add(item)
        elif tile == TILEMAP.HEALTH_TILE_ID:
            item = ItemBox(rect.x, rect.y, 'health')
            self.groups['item'].add(item)
        elif tile == TILEMAP.LEVEL_EXIT_TILE_ID:
            exit_tile = GameTile(img, rect.x, rect.y)
            self.groups['exit'].add(exit_tile)


    def load_next_level(self):
        '''
        Advances Player to the next level.
        '''
        self.level += 1
        if exists(f'level{self.level}_data.csv'):
            self.load_current_level()
        else:
            print(f'Error: level {self.level} does not exist')
            self.game_mode = GameModes.QUIT


    def load_current_level(self) -> Player:
        '''
        Loads the starting world state for the given level.
        '''

        # Read the level data from a CSV file
        self.reset_world()
        self.world_data = []
        with open(f'level{self.level}_data.csv', 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for idx_y, row_of_tiles in enumerate(reader):
                self.world_data.append([])
                for idx_x, tile_data in enumerate(row_of_tiles):
                    self.world_data[idx_y].append(int(tile_data))

        # Populate the world by loading the appropriate game tile
        self.world_width = TILEMAP.TILE_SIZE * len(self.world_data[0])
        for idx_y, row_of_tiles in enumerate(self.world_data):
            for idx_x, tile in enumerate(row_of_tiles):
                if tile >= 0: # -1 is an empty space
                    self.load_game_tile(tile, idx_x, idx_y)
    

    def player_actions(self, controller):
        '''
        Handles possible player actions based on the buttons that are pressed
        on the controller.
        '''

        # Ideally, this code would be within the Player class, but only the
        # game engine knows about the bullet and grenade groups.
        self.player.move(controller.mleft, controller.mright, controller.jump)
        if controller.shoot:
            bullet = self.player.shoot()
            if bullet:
                self.groups['bullet'].add(bullet)
        if controller.throw:
            grenade = self.player.throw()
            if grenade:
                self.groups['grenade'].add(grenade)


    def enemy_actions(self):
        '''
        Handle AI behavior for all enemies.
        '''
        # We keep dead enemies on the screen; only let live ones to do things
        for enemy in self.groups['enemy']:
            if enemy.alive:
                if enemy.vision.colliderect(self.player.rect):
                    bullet = enemy.shoot()
                    if bullet:
                        self.groups['bullet'].add(bullet)
                enemy.ai_move(self.world_data, TILEMAP.TILE_SIZE)
                if enemy.health <= 0:
                    enemy.death()


    def collect_item_boxes(self):
        ''' 
        Check if player collected any item boxes and add to inventory.
        '''
        for item in spritecollide(self.player, self.groups['item'], True):
            if item.box_type == 'ammo':
                amount = self.player.ammo + item.quantity
                self.player.ammo += min(amount, self.player.max_ammo)
            elif item.box_type == 'grenade':
                amount = self.player.grenades + item.quantity
                self.player.grenades += min(amount, self.player.max_grenades)
            elif item.box_type == 'health':
                amount = self.player.health + item.quantity
                self.player.health = min(amount, self.player.max_health)
    

    def handle_bullet_damage(self):
        '''
        Check for bullet hit damage and injure Soldier accordingly.
        '''
        for bullet in spritecollide(self.player, self.groups['bullet'], True):
            self.player.health -= bullet.damage
        for enemy in self.groups['enemy']:
            for bullet in spritecollide(enemy, self.groups['bullet'], False):
                if enemy.health >= 0:
                    enemy.health -= bullet.damage
                    bullet.kill()
        for obstacle in self.groups['obstacle']:
            for bullet in spritecollide(obstacle, self.groups['bullet'], False):
                bullet.kill()


    def make_grenades_explode(self):
        '''
        Check for exploding grenades and initiate animation.
        '''
        # Animate with an explosion and calculate damage against all Soldiers
        for grenade in self.groups['grenade']:
            if grenade.do_explosion:
                explosion = Explosion(grenade.rect.x, grenade.rect.y)
                self.groups['explosion'].add(explosion)
                self.player.health -= grenade.damage_at(self.player.rect)
                for enemy in self.groups['enemy']:
                    enemy.health -= grenade.damage_at(enemy.rect)
                grenade.kill()
    

    def check_for_player_death(self):
        '''
        Determines if the player has died and updates object accordingly.
        '''
        if (self.player.health <= 0 
                or self.player.rect.top > SCREEN_HEIGHT
                or spritecollide(self.player, self.groups['water'], False)):
            self.player.death()


    def check_if_level_exit(self):
        '''
        Determines if the player has finished the current level.
        '''
        if spritecollide(self.player, self.groups['exit'], False):
            self.level_complete = True


    def shift_camera(self):
        '''
        Moves camera left and right as Player moves to the side of the screen.
        '''

        # If the player is moving too far right or left, scroll the screen
        if ((self.player.direction == Direction.RIGHT 
                and self.player.rect.right + self.camera_scroll >= SCROLL_RIGHT
                and self.bg_scroll + SCREEN_WIDTH < self.world_width)
            or (self.player.direction == Direction.LEFT 
                and self.player.rect.left + self.camera_scroll < SCROLL_LEFT
                and self.bg_scroll > 0)):
            self.camera_scroll -= self.player.dx
            self.bg_scroll += self.player.dx


    def apply_physics(self, sprite):
        '''
        Calculates and moves a sprite's position based on its current velocity
        and the effect of gravity.
        '''
        # Calculate vertical movement
        sprite.vel_y += ENVIRONMENT.GRAVITY
        sprite.vel_y = min(20, sprite.vel_y)
        sprite.dy = int(sprite.vel_y)

        # Calculate lateral movement
        sprite.dx = int(sprite.vel_x * sprite.direction.value)

        # Detect collisions with wall (x) and ground (y) obstacles
        for tile in self.groups['obstacle']:
            predicted_x = pygame.Rect(sprite.rect.x + sprite.dx, sprite.rect.y,
                                      sprite.rect.width, sprite.rect.height)
            if tile.rect.colliderect(predicted_x):
                if sprite.direction == Direction.LEFT:
                    sprite.dx = tile.rect.right - sprite.rect.left
                elif sprite.direction == Direction.RIGHT:
                    sprite.dx = tile.rect.left - sprite.rect.right
                sprite.vel_x = 0
            predicted_y = pygame.Rect(sprite.rect.x, sprite.rect.y + sprite.dy,
                                      sprite.rect.width, sprite.rect.height)
            if tile.rect.colliderect(predicted_y):
                if sprite.vel_y < 0: # jumping and hitting head
                    sprite.dy = tile.rect.bottom - sprite.rect.top
                if sprite.vel_y > 0:
                    sprite.landed(sprite.vel_y)
                    sprite.dy = tile.rect.top - sprite.rect.bottom
                sprite.vel_y = 0

        # Check if player is going off the edge of the world
        if ((sprite.direction == Direction.RIGHT 
                and sprite.rect.right >= self.world_width)
            or (sprite.direction == Direction.LEFT
                and sprite.rect.left <= 0)):
            sprite.dx = 0

        # Move the sprite
        sprite.rect.x += sprite.dx
        sprite.rect.y += sprite.dy


    def update(self, controller):
        '''
        Updates the world environment based on any buttons pressed on the
        controller, the inherent movement of the objects through the world,
        and sprite collisions. Instead of returning a value, this function
        updates internal variables that represent the state of the world.
        '''

        # Calculate player movements
        if self.player.alive:
            self.player_actions(controller)
            self.apply_physics(self.player)
            self.shift_camera()

        # Calculate enemy and grenade movements
        self.enemy_actions()
        for enemy in self.groups['enemy']:
            self.apply_physics(enemy)
        for grenade in self.groups['grenade']:
            self.apply_physics(grenade)

        # Special collision-based updates
        self.collect_item_boxes()
        self.handle_bullet_damage()
        self.make_grenades_explode()

        # Standard updates to all sprite groups
        self.player.update()
        for group in self.groups.values():
            group.update()

        # Check for end-states
        self.check_for_player_death()
        self.check_if_level_exit()


    def draw(self):
        '''
        Blits all of the sprites in the entire world onto the screen.
        '''
        # Draw the background graphics: sky, mountains, trees, etc.
        # The y-coordinates are offset so that the scene appears correctly
        # (e.g., clouds on top, then mountains, trees on bottom).
        # But the x-coordinates are staggered so that we get a semi-3D effect
        # as the player moves through the level.
        # We draw 5 copies of each image to extend the background through
        # the whole level as the screen scrolls along.
        for copy_num in range(5):
            for idx in range(len(GameEngine.bg_img)):
                bg_img = GameEngine.bg_img[idx]
                bg_y = int(GameEngine.bg_ypos[idx])
                bg_x = int((copy_num * GameEngine.bg_width)
                           - self.bg_scroll * (0.5 + idx * 0.1))
                self.screen.blit(bg_img, (bg_x, bg_y))

        # Draw the world one tile at a time
        for group in self.group_names:
            for sprite in self.groups[group]:
                sprite.draw(self.screen, self.camera_scroll)
        self.player.draw(self.screen, self.camera_scroll)

        # Draw the status bars
        self.health_bar.draw(self.screen, self.player.health)
        self.grenade_bar.draw(self.screen, f'GRENADES: {self.player.grenades}')
        self.ammo_bar.draw(self.screen, f'ROUNDS: {self.player.ammo}')


class GameTile(pygame.sprite.Sprite):
    '''
    An object representing one of the many game tiles.
    '''
    def __init__(self, img, x, y):
        '''
        Initializes the look and position of a game tile.
        '''
        super().__init__()
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def draw(self, screen, screen_scroll):
        '''
        Draws the game tile to the given screen surface.
        '''
        screen.blit(self.image, (self.rect.x + screen_scroll, self.rect.y))


class TextBar():
    '''
    Text to visualize the player's stats.
    '''

    font = None

    @classmethod
    def load_assets(cls):
        '''
        Preload font renderer into shared memory for reuse.
        '''
        if cls.font is None:
            cls.font = pygame.font.SysFont('Futura', 30)

    def __init__(self, x, y, color):
        '''
        Initializes a status bar with the starting value.
        '''
        TextBar.load_assets()
        self.x, self.y = x, y
        self.color = color

    def draw(self, screen, text):
        '''
        Draws a particular statistics to the given screen surface.
        '''
        img = TextBar.font.render(text, True, self.color)
        screen.blit(img, (self.x, self.y))


class HealthBar():
    '''
    Graphic to visualize the player's health as a green/red rectangle.
    '''

    def __init__(self, x, y, max_health, width=150, height=20):
        '''
        Initializes a player's health bar with the full health value.
        '''
        self.x, self.y = x, y
        self.width = width
        self.height = height
        self.max_health = max_health

    def draw(self, screen, health):
        '''
        Draws the player's health bar to the given screen surface.
        '''
        health_size = min(self.width, self.width * health / self.max_health)
        outline_rect = (self.x-1, self.y-1, self.width+2, self.height+2)
        green_rect = (self.x, self.y, health_size, self.height)
        red_rect = (self.x, self.y, self.width, self.height)
        rect(screen, COLOR.WHITE, outline_rect)
        rect(screen, COLOR.RED, red_rect)
        rect(screen, COLOR.GREEN, green_rect)
