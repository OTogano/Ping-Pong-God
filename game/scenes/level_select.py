"""Level select: four cards in a row. Beat a level to unlock the next one.

Unlocked cards show the opponent's portrait (in their kit colours).
Locked cards show a black silhouette and a padlock. Beaten levels get a star.
"""

import math

import pygame

from game import controls
from game import settings as S
from game.gfx.sprites import load_image, recolour_surface
from game.gfx.text import BitmapFont
from game.gfx.ui import dim, panel
from game.levels import LEVELS
from game.scenes.base import Scene

CARD_W, CARD_H, GAP = 60, 76, 4
CARDS_Y = 52
PORTRAIT_BOX = 30  # dark square behind the portrait
SHAKE_TIME = 0.3  # a locked card shakes when you try to open it
INFO_Y = 150  # line under the cards: opponent, points to win, or why it's locked


class LevelSelectScene(Scene):
    def __init__(self, index=0):
        self.font = BitmapFont()
        self.background = load_image("ui", "title_bg.png")
        portrait = load_image("sprites", "portrait.png")
        self.lock = load_image("ui", "lock.png")
        self.star = load_image("ui", "star.png")
        # One portrait per level in that opponent's kit, plus a black silhouette for locked cards.
        # One portrait per level: the opponent's own, or the player's in their kit.
        # Locked cards show the same face as a black silhouette.
        self.portraits = [
            load_image("sprites", f"{level.portrait}.png")
            if level.portrait
            else recolour_surface(portrait, level.kit)
            for level in LEVELS
        ]
        self.silhouettes = []
        for face in self.portraits:
            shadow = face.copy()
            shadow.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            self.silhouettes.append(shadow)
        self.index = index
        self.shake = 0.0
        self.notice = ""

    # ---------------------------------------------------------------- input
    def handle_event(self, event):
        if not self.app:
            return
        if controls.pressed(event, controls.LEFT):
            self._move(-1)
        elif controls.pressed(event, controls.RIGHT):
            self._move(1)
        elif controls.pressed(event, controls.CONFIRM):
            if self.app.progress.is_unlocked(self.index):
                from game.scenes.match import Match  # avoids a circular import

                self.app.switch(Match(self.index))
            else:
                self.shake = SHAKE_TIME
                self.notice = f"Beat {LEVELS[self.index - 1].name} to unlock"
        elif controls.pressed(event, controls.BACK):
            from game.scenes.title import TitleScene

            self.app.switch(TitleScene())

    def _move(self, step):
        self.index = (self.index + step) % len(LEVELS)
        self.notice = ""

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt)

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        surf.blit(self.background, (0, 0))
        dim(surf)
        self.font.draw(surf, "Select level", (S.WIDTH // 2, 16))
        x0 = (S.WIDTH - (len(LEVELS) * CARD_W + (len(LEVELS) - 1) * GAP)) // 2
        for i in range(len(LEVELS)):
            self._draw_card(surf, i, x0 + i * (CARD_W + GAP))

        # Black strips behind the info line and the controls so they stay readable.
        panel(surf, pygame.Rect(-1, INFO_Y - 5, S.WIDTH + 2, 18))
        panel(surf, pygame.Rect(-1, S.HEIGHT - 19, S.WIDTH + 2, 20))
        level = LEVELS[self.index]
        if self.notice:
            self.font.draw(surf, self.notice, (S.WIDTH // 2, INFO_Y), color=S.COL_GOLD)
        elif self.app and self.app.progress.is_unlocked(self.index):
            self.font.draw(
                surf,
                f"vs {level.opponent}: first to {level.points_to_win}",
                (S.WIDTH // 2, INFO_Y),
            )
        else:
            self.font.draw(surf, "Locked", (S.WIDTH // 2, INFO_Y), color=S.COL_MENU_DIM)
        self.font.draw(
            surf,
            "A/D: choose   Enter: play   Esc: back",
            (S.WIDTH // 2, S.HEIGHT - 13),
            color=S.COL_MENU_DIM,
        )

    def _draw_card(self, surf, i, x):
        progress = self.app.progress if self.app else None
        unlocked = progress is not None and progress.is_unlocked(i)
        selected = i == self.index
        y = CARDS_Y - (4 if selected else 0)  # the selected card lifts up
        if selected and self.shake > 0:
            x += round(math.sin(self.shake * 60) * 2)

        card = pygame.Rect(x, y, CARD_W, CARD_H)
        pygame.draw.rect(surf, S.COL_PANEL, card)
        pygame.draw.rect(
            surf,
            S.COL_GOLD if selected else S.COL_PANEL_BORDER,
            card,
            2 if selected else 1,
        )

        box = pygame.Rect(0, 0, PORTRAIT_BOX, PORTRAIT_BOX)
        box.midtop = (card.centerx, y + 6)
        pygame.draw.rect(surf, S.COL_PORTRAIT_BG, box)
        face = self.portraits[i] if unlocked else self.silhouettes[i]
        surf.blit(face, face.get_rect(midbottom=box.midbottom))
        if not unlocked:
            surf.blit(
                self.lock, self.lock.get_rect(center=(box.centerx, box.bottom - 4))
            )
        if progress is not None and progress.beaten[i]:
            surf.blit(self.star, (card.right - 11, y + 2))

        name_color = None if unlocked else S.COL_MENU_DIM
        self.font.draw(surf, LEVELS[i].name, (card.centerx, y + 42), color=name_color)
        opponent = LEVELS[i].opponent if unlocked else "???"
        if self.font.width(opponent) > CARD_W - 4:  # e.g. "Coach Greg" -> two lines
            opponent = opponent.replace(" ", "\n", 1)
        self.font.draw(surf, opponent, (card.centerx, y + 54), color=S.COL_MENU_DIM)
