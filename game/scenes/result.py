"""Shown over the finished match: win or lose, the score, and what to do next."""

import pygame

from game import controls
from game import settings as S
from game.gfx.text import BitmapFont
from game.gfx.ui import Menu, dim, panel
from game.scenes.base import Scene


class ResultScene(Scene):
    is_overlay = True

    def __init__(
        self,
        won,
        score,
        retry,
        level_select,
        next_level=None,
        unlocked=None,
        champion=False,
    ):
        """won: did the player win. score: e.g. "3 - 1".
        retry / level_select / next_level: functions for the menu options
        (next_level is None when there is no next level to continue to).
        unlocked: name of a level this win unlocked, if any.
        champion: True after beating the final level."""
        self.font = BitmapFont()
        self.won, self.score = won, score
        self.unlocked, self.champion = unlocked, champion
        self.level_select = level_select
        items = []
        if won and next_level:
            items.append(("Continue", next_level))
        items.append(("Play again" if won else "Retry", retry))
        items.append(("Level select", level_select))
        self.menu = Menu(items)

    def handle_event(self, event):
        if controls.pressed(event, controls.BACK):
            self.level_select()
        else:
            self.menu.handle_event(event)

    def draw(self, surf):
        dim(surf)
        lines = ["You win!" if self.won else "You lose!", self.score]
        extra = (
            "Champion!"
            if self.champion
            else (f"{self.unlocked} unlocked!" if self.unlocked else "")
        )
        box = pygame.Rect(0, 0, 170, 62 + len(self.menu.items) * S.MENU_LINE)
        box.center = (S.WIDTH // 2, S.HEIGHT // 2)
        panel(surf, box)
        self.font.draw(
            surf,
            lines[0],
            (box.centerx, box.top + 8),
            color=S.COL_GOLD if self.won else None,
        )
        self.font.draw(surf, lines[1], (box.centerx, box.top + 20))
        if extra:
            self.font.draw(surf, extra, (box.centerx, box.top + 32), color=S.COL_GOLD)
        self.menu.draw(surf, self.font, box.centerx, box.top + 50)
