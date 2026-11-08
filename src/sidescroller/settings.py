
from enum import IntEnum
from dataclasses import dataclass

# Display screen
FPS = 60
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = int(SCREEN_WIDTH * 0.6)
SCROLL_THRESHOLD = SCREEN_WIDTH // 4
SCROLL_RIGHT = SCROLL_THRESHOLD #SCROLL_THRESHOLD 
SCROLL_LEFT = SCREEN_WIDTH - SCROLL_THRESHOLD #SCROLL_THRESHOLD

class GameModes(IntEnum):
    MENU = 0
    PLAY = 1
    QUIT = 2

class CounterType(IntEnum):
    FRAME_BASED = 0  # for AI agents who train in the background at ultraspeed
    TIME_BASED = 1   # for humans who play the game interactively in real-time

@dataclass(frozen=True)
class EnvironmentSettings:
    GRAVITY = 0.75
    SOLDIER_JUMP_STRENGTH = -13
    MAX_HEALTH = 100
    MAX_AMMO = 50
    MAX_GRENADES = 10
    BULLET_FULL_DAMAGE = 25
    BULLET_VELOCITY_X = 15
    GRENADE_FULL_DAMAGE = 100
    GRENADE_INNER_RADIUS = 50  # pixels from grenade
    GRENADE_OUTER_RADIUS = 200 # pixels from grenade
    GRENADE_VELOCITY_X = 7
    GRENADE_VELOCITY_Y = -11
    SOLDIER_SCALE = 1.65
    # if using get_ticks
    GRENADE_FUSE_TIME = 1500
    PLAYER_SHOOT_DELAY = 200
    PLAYER_THROW_DELAY = 1500
    SOLDIER_SHOOT_DELAY = 500
    SOLDIER_THROW_DELAY = 2000
    ANIMATION_DELAY = 100
    # if using frame counter @ 60fps
    GRENADE_COOLDOWN = 90
    PLAYER_SHOOT_COOLDOWN = 12
    PLAYER_THROW_COOLDOWN = 90
    SOLDIER_SHOOT_COOLDOWN = 30
    SOLDIER_THROW_COOLDOWN = 120
    ANIMATION_COOLDOWN = 6

# TODO: define TILE_SIZE from the image dimensions instead of hardcoded value
@dataclass(frozen=True)
class TileMapSettings:
    ROWS = 16
    COLS = 150
    TILE_SIZE = SCREEN_HEIGHT // ROWS
    TILE_TYPE_COUNT = 21
    EMPTY_TILE = -1
    DIRT_TILE_FIRST = 0
    DIRT_TILE_LAST = 8
    WATER_TILE_FIRST = 9
    WATER_TILE_LAST = 10
    DECORATION_TILE_FIRST = 11
    DECORATION_TILE_LAST = 14
    PLAYER_TILE_ID = 15
    ENEMY_TILE_ID = 16
    AMMO_TILE_ID = 17
    GRENADE_TILE_ID = 18
    HEALTH_TILE_ID = 19
    LEVEL_EXIT_TILE_ID = 20

@dataclass(frozen=True)
class ColorSettings:
# Drawing colors
    BACKGROUND = (144, 201, 120)
    BLACK = (32, 32, 32)
    WHITE = (255, 255, 255)
    GREEN = (0, 255, 0)
    PINK = (235, 65, 54)
    RED = (255, 0, 0)

# Initialize settings objects
ENVIRONMENT = EnvironmentSettings()
TILEMAP = TileMapSettings()
COLOR = ColorSettings

# Soldier animations
class Action(IntEnum):
    IDLE = 0
    RUN = 1
    JUMP = 2
    DEATH = 3

class Direction(IntEnum):
    LEFT = -1
    RIGHT = 1
    IDLE = 0
    def reverse(self):
        return Direction(-self.value)
    def pause(self):
        return Direction(0)
    def __mul__(self, operand):
        if operand == -1:
            return Direction(-self.value)
        raise ValueError("Multiplication only support -1 to reverse direction")

# Shared RL defaults. Registered environments delegate the limit to TimeLimit.
DEFAULT_EPISODE_STEPS = 1000


@dataclass(frozen=True)
class RewardSettings:
    progress: float = 0.1
    shoot: float = -10_000.0
    throw: float = -10_000.0
    death: float = -100_000.0
    completion: float = 100_000.0
