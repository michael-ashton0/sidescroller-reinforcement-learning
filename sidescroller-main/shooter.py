# Initialize the display and sound before importing any other modules
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR
pygame.init()
pygame.mixer.init()
pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Shooter')

# Now import the other modules, which may depend on the mixer and display
from controller import GameController
from widgets import GameButton, GameFade, FadeType
from engine import GameEngine, GameModes

# Create IO devices:
#  1) controller for input
#  2) graphic display for output
#  3) a clock to keep time
#  4) a font to write text
controller = GameController()
engine = GameEngine()
screen = pygame.display.get_surface()
clock = pygame.time.Clock()


def handle_keyboard_events(event: pygame.event.Event, 
                           controller: GameController) -> GameController:
    ''' 
    Process player keystrokes and returns the current button combination.
    '''

    # Find which keys have been pressed
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_LEFT:
            controller.mleft = True
        if event.key == pygame.K_RIGHT:
            controller.mright = True
        if event.key == pygame.K_UP:
            controller.jump = True
        if event.key == pygame.K_SPACE:
            controller.shoot = True
        if event.key == pygame.K_q:
            controller.throw = True

    # Find which keys have been released
    if event.type == pygame.KEYUP:
        if event.key == pygame.K_LEFT:
            controller.mleft = False
        if event.key == pygame.K_RIGHT:
            controller.mright = False
        if event.key == pygame.K_UP:
            controller.jump = False
        if event.key == pygame.K_SPACE:
            controller.shoot = False    
        if event.key == pygame.K_q:
            controller.throw = False
    
    # Return the current state of the controller
    return controller


def run_main_menu(engine: GameEngine, 
                  controller: GameController, 
                  screen: pygame.Surface,
                  events: pygame.event) -> None:
    '''
    Displays the main menu. This interface is the primary method for human
    players to click on a button and start a new, interactive game.
    '''

    # Draw the main menu
    screen.fill(COLOR.BACKGROUND)
    start_button.draw(screen)
    exit_button.draw(screen)

    # Handle button clicks
    if start_button.is_clicked():
        engine.game_mode = GameModes.INTERACTIVE
        engine.load_current_level()
        intro_fade.begin_fade()
    if exit_button.is_clicked():
        engine.game_mode = GameModes.QUIT

    # Handle the various ways to quit game
    for event in events:
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                or event.type == pygame.QUIT):
            engine.game_mode = GameModes.QUIT

    # Nothing particularly important to return
    return None


def run_interactive_game(engine: GameEngine,
                         controller: GameController, 
                         screen: pygame.Surface,
                         events: pygame.event) -> None:
    '''
    Plays an interactive game between a human player and the computer AI. If
    the player advances to the next level, we will stay in interactive mode.
    But if the player dies, we will return to the main menu.
    '''

    # Update the position of all physics-controlled sprites
    engine.update(controller)
    engine.draw(screen)

    # Special case #1: begin a new level
    if not intro_fade.finished:
        intro_fade.draw_fade(screen)

    # Special case #2: player dies, restart same level
    if not engine.player.alive:
        if not death_fade.started:
            death_fade.begin_fade()
        if not death_fade.finished:
            death_fade.draw_fade(screen)
        else:
            death_fade.end_fade()
            engine.load_current_level()
            engine.game_mode = GameModes.MENU

    # Special case #3: player advances to the next level
    if engine.level_complete:
        if not level_fade.started:
            level_fade.begin_fade()
        if not level_fade.finished:
            level_fade.draw_fade(screen)
        else:
            level_fade.end_fade()
            engine.game_mode = GameModes.INTERACTIVE
            engine.load_next_level()
            intro_fade.begin_fade()

    # Handle the various controller inputs to the game
    for event in events:
        if event.type == pygame.QUIT:
            engine.game_mode = GameModes.QUIT
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            engine.game_mode = GameModes.QUIT
        controller = handle_keyboard_events(event, controller)

    # Nothing particularly important to return
    return None


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
    while engine.game_mode != GameModes.QUIT:
        events = pygame.event.get()
        if engine.game_mode == GameModes.MENU:
            run_main_menu(engine, controller, screen, events)
        elif engine.game_mode == GameModes.INTERACTIVE:
            run_interactive_game(engine, controller, screen, events)
            health_pct = engine.player.health / engine.player.max_health
        clock.tick(FPS)
        pygame.display.flip()
    pygame.quit()
