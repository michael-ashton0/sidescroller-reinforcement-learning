import pygame
from sidescroller.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from enum import IntEnum


class MouseButton(IntEnum):
    LEFT_MBUTTON = 0
    MIDDLE_MBUTTON = 1
    RIGHT_MBUTTON = 2

class GameButton():
    '''
    A simple button for a PyGame GUI window.
    '''

    def __init__(self, image, x, y, scale=1.0):
        '''
        Initializes the button's image and location.
        '''
        width = int(image.get_width() * scale)
        height = int(image.get_height() * scale)
        self.image = pygame.transform.scale(image, (width, height))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.clicked = False

    def draw(self, screen):
        '''
        Draws the button to the given screen surface.
        '''
        screen.blit(self.image, (self.rect.x, self.rect.y))
	
    def is_clicked(self):
        '''
        Returns True if the button is clicked.
        '''
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()
        if self.rect.collidepoint(mouse_pos):
            if mouse_clicked[MouseButton.LEFT_MBUTTON] and not self.clicked:
                self.clicked = True
                return True
        else:
            self.clicked = False
        return False
    
    def reset(self):
        '''
        Resets the button after it has been clicked.
        '''
        self.clicked = False


class FadeType(IntEnum):
    INTRO_EVENT = 0
    LEVEL_EVENT = 1
    DEATH_EVENT = 2

class GameFade():
    '''
    An object for visually transitioning from one part of the game to another.
    '''

    def __init__(self, fade_type, color, speed=5):
        '''
        Initializes a string fade object according to the allowed types.
        '''
        self.fade_type = fade_type
        self.color = color
        self.speed = speed
        self.counter = 0
        self.started = False
        self.finished = True

    def begin_fade(self):
        '''
        Begins drawing a fade animation sequence.
        '''     
        self.counter = 0
        self.started = True
        self.finished = False

    def end_fade(self):
        self.started = False

    def draw_fade(self, screen):
        '''
        Draws a frame from a screen fade animation baed on the fade type.
        '''
        if self.fade_type == FadeType.INTRO_EVENT:
            pygame.draw.rect(screen, self.color, (0 - self.counter, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.color, (SCREEN_WIDTH // 2 + self.counter, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.color, (0, 0 - self.counter, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
            pygame.draw.rect(screen, self.color, (0, SCREEN_HEIGHT // 2 + self.counter, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        
        elif self.fade_type == FadeType.LEVEL_EVENT:
            pygame.draw.rect(screen, self.color, (0, 0, self.counter, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.color, (SCREEN_WIDTH - self.counter, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.color, (0, 0, SCREEN_WIDTH, self.counter))
            pygame.draw.rect(screen, self.color, (0, SCREEN_HEIGHT - self.counter, SCREEN_WIDTH, SCREEN_HEIGHT))

        elif self.fade_type == FadeType.DEATH_EVENT:
            pygame.draw.rect(screen, self.color, (0, 0, SCREEN_WIDTH, self.counter))
        
        # Stop when we reach a certain point.
        self.counter += self.speed
        if self.counter >= SCREEN_WIDTH:
            self.finished = True

