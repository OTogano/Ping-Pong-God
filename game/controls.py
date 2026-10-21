"""Menu controls: arrows or W A S D to move, Enter/Space to pick, Esc to go back.

Gameplay keys (D F J K) live in settings.HIT_KEYS. Menus and matches never
read input at the same time, so D can mean "right" in a menu safely.
"""

import pygame

UP = (pygame.K_UP, pygame.K_w)
DOWN = (pygame.K_DOWN, pygame.K_s)
LEFT = (pygame.K_LEFT, pygame.K_a)
RIGHT = (pygame.K_RIGHT, pygame.K_d)
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
BACK = (pygame.K_ESCAPE,)


def pressed(event, keys):
    """True if this event is a key press of one of `keys`."""
    return event.type == pygame.KEYDOWN and event.key in keys
