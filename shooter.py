
import pygame
from pygame.event import Event
from controller import GameController
from widgets import GameButton, GameFade, FadeType
from engine import GameEngine
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR, GameModes

pygame.init()
pygame.mixer.init()
pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Shooter')

class InteractiveShooter():

    def __init__(self):
        # Create IO devices:
        #  1) graphic display for output
        #  2) controller for input
        #  3) the main game engine
        #  4) a clock to keep time
        self.screen = pygame.display.get_surface()
        self.controller = GameController()
        self.engine = GameEngine(self.screen, time_based=True)
        self.clock = pygame.time.Clock()
        self.game_mode = GameModes.MENU


    def handle_keyboard_events(self, event:Event) -> None:
        ''' 
        Process player keystrokes and returns the current button combination.
        '''

        # Find which keys have been pressed
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.controller.mleft = True
            if event.key == pygame.K_RIGHT:
                self.controller.mright = True
            if event.key == pygame.K_UP:
                self.controller.jump = True
            if event.key == pygame.K_SPACE:
                self.controller.shoot = True
            if event.key == pygame.K_q:
                self.controller.throw = True

        # Find which keys have been released
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                self.controller.mleft = False
            if event.key == pygame.K_RIGHT:
                self.controller.mright = False
            if event.key == pygame.K_UP:
                self.controller.jump = False
            if event.key == pygame.K_SPACE:
                self.controller.shoot = False    
            if event.key == pygame.K_q:
                self.controller.throw = False


    def main_menu(self, events: pygame.event) -> None:
        '''
        Displays the main menu. This interface is the primary method for human
        players to click on a button and start a new, interactive game.
        '''

        # Draw the main menu
        self.screen.fill(COLOR.BACKGROUND)
        start_button.draw(self.screen)
        exit_button.draw(self.screen)

        # Handle button clicks
        if start_button.is_clicked():
            self.game_mode = GameModes.PLAY
            self.engine.load_current_level()
            intro_fade.begin_fade()
        if exit_button.is_clicked():
            self.game_mode = GameModes.QUIT

        # Handle the various ways to quit game
        for event in events:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    or event.type == pygame.QUIT):
                self.game_mode = GameModes.QUIT


    def interactive_game(self, events: pygame.event) -> None:
        '''
        Plays an interactive game between a human player and the computer AI.
        If the player advances to the next level, we will stay in interactive
        mode. But if the player dies, we will return to the main menu.
        '''

        # Update the position of all physics-controlled sprites
        self.engine.update(self.controller)
        self.engine.draw()

        # Special case #1: begin a new level
        if not intro_fade.finished:
            intro_fade.draw_fade(self.screen)

        # Special case #2: player dies, restart same level
        if not self.engine.player.alive:
            if not death_fade.started:
                death_fade.begin_fade()
            if not death_fade.finished:
                death_fade.draw_fade(self.screen)
            else:
                death_fade.end_fade()
                self.engine.load_current_level()
                self.game_mode = GameModes.MENU

        # Special case #3: player advances to the next level
        if self.engine.level_complete:
            if not level_fade.started:
                level_fade.begin_fade()
            if not level_fade.finished:
                level_fade.draw_fade(self.screen)
            else:
                level_fade.end_fade()
                self.game_mode = GameModes.PLAY
                if not self.engine.load_next_level():
                    print(f'Error: level {self.engine.level+1} does not exist')
                    self.game_mode = GameModes.QUIT
                    

                intro_fade.begin_fade()

        # Handle the various controller inputs to the game
        for event in events:
            if event.type == pygame.QUIT:
                self.game_mode = GameModes.QUIT
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_mode = GameModes.QUIT
            self.handle_keyboard_events(event)


if __name__ == '__main__':
    '''
    Entry point to the program, runs the main game loop.
    '''

    # Create the buttons for use on the main menudisplay
    start_button_img = pygame.image.load('img/start_btn.png').convert_alpha()
    start_button_x = SCREEN_WIDTH // 2 - start_button_img.get_width() // 2
    start_button_y = SCREEN_HEIGHT // 2 - start_button_img.get_height() - 100
    start_button = GameButton(start_button_img, start_button_x, start_button_y)
    exit_button_img = pygame.image.load('img/exit_btn.png').convert_alpha()
    exit_button_x = SCREEN_WIDTH // 2 - exit_button_img.get_width() // 2
    exit_button_y = SCREEN_HEIGHT // 2 - exit_button_img.get_height() + 100
    exit_button = GameButton(exit_button_img, exit_button_x, exit_button_y)

    # Define notable game transitions
    intro_fade = GameFade(FadeType.INTRO_EVENT, COLOR.BLACK)
    level_fade = GameFade(FadeType.LEVEL_EVENT, COLOR.BLACK)
    death_fade = GameFade(FadeType.DEATH_EVENT, COLOR.PINK)

    # The main game loop has several states, each handled separately:
    #   1. 'Menu' where the player can choose between options
    #   2. 'Interactive' where a human player plays the game
    shooter = InteractiveShooter()
    while shooter.game_mode != GameModes.QUIT:
        events = pygame.event.get()
        if shooter.game_mode == GameModes.MENU:
            shooter.main_menu(events)
        elif shooter.game_mode == GameModes.PLAY:
            shooter.interactive_game(events)
        shooter.clock.tick(FPS)
        pygame.display.flip()
    pygame.quit()
