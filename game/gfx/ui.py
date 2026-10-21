"""Things that appear in every level: the umpire flip-board and the key icons."""

import json
import os

import pygame

from game import settings as S
from game.gfx.sprites import load_image, load_strip


class FlipCard:
    """One split-flap card. When the number changes, the top half of the old
    number folds down to the seam, then the bottom half of the new one unfolds."""

    def __init__(self, digits, pos):
        self.digits, self.pos = digits, pos
        self.value = self.prev = 0
        self.t = 1.0  # flip progress, 1 = finished

    def set(self, value):
        value = min(value, 9)  # one card shows 0-9
        if value != self.value:
            self.prev, self.value, self.t = self.value, value, 0.0

    def update(self, dt):
        self.t = min(1.0, self.t + dt / S.FLIP_TIME)

    def draw(self, surf):
        x, y = self.pos
        new, old = self.digits[self.value], self.digits[self.prev]
        w, h = new.get_size()
        half = h // 2
        if self.t >= 1.0:
            surf.blit(new, (x, y))
            return
        # Behind the flap: the new top half and the old bottom half.
        surf.blit(new, (x, y), (0, 0, w, half))
        surf.blit(old, (x, y + half), (0, half, w, h - half))
        if self.t < 0.5:  # old top half folding down: squash it toward the seam
            src, size = old.subsurface((0, 0, w, half)), round(half * (1 - self.t * 2))
            rect = pygame.Rect(x, y + half - size, w, size)
        else:  # new bottom half unfolding from the seam
            src, size = (
                new.subsurface((0, half, w, h - half)),
                round((h - half) * (self.t * 2 - 1)),
            )
            rect = pygame.Rect(x, y + half, w, size)
        if size > 0:
            surf.fill(S.COL_CARD, rect.inflate(2, 0))  # the flap's face
            surf.blit(pygame.transform.scale(src, rect.size), rect)
            edge_y = rect.top if self.t < 0.5 else rect.bottom - 1
            surf.fill(S.COL_CARD_EDGE, (rect.x - 1, edge_y, w + 2, 1))  # flap edge


class Scoreboard:
    def __init__(self):
        self.board = load_image("ui", "scoreboard.png")
        with open(
            S.resource_path(os.path.join("assets", "ui", "scoreboard.json")),
            encoding="utf-8",
        ) as f:
            meta = json.load(f)
        digits = load_strip(os.path.join("ui", "digits.png"), meta["digit_size"][0])
        bx, by = S.SCOREBOARD_POS
        # Card 0 is CPU, card 1 is YOU (matches the labels on the board).
        self.cards = [
            FlipCard(digits, (bx + sx, by + sy)) for sx, sy in meta["digit_slots"]
        ]

    def set(self, cpu, you):
        self.cards[0].set(cpu)
        self.cards[1].set(you)

    def update(self, dt):
        for card in self.cards:
            card.update(dt)

    def draw(self, surf):
        surf.blit(self.board, S.SCOREBOARD_POS)
        for card in self.cards:
            card.draw(surf)


class KeyIcons:
    """D F J K keycaps beside each spot. Rows in keys.png: normal, lit, pressed."""

    NORMAL, LIT, PRESSED = 0, 1, 2

    def __init__(self):
        sheet = load_image("ui", "keys.png")
        size = sheet.get_width() // 4
        self.icons = [
            [
                sheet.subsurface((k * size, row * size, size, size)).copy()
                for row in range(3)
            ]
            for k in range(4)
        ]
        self.pressed = [0.0] * 4

    def press(self, index):
        self.pressed[index] = S.KEY_PRESS_SHOW

    def update(self, dt):
        self.pressed = [max(0.0, t - dt) for t in self.pressed]

    def draw(self, surf, lit=None):
        for i, pos in enumerate(S.KEY_ICON_POS):
            state = (
                self.PRESSED
                if self.pressed[i] > 0
                else (self.LIT if i == lit else self.NORMAL)
            )
            surf.blit(self.icons[i][state], pos)
