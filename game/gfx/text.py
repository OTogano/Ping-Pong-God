"""Pixel-font text, drawn from assets/ui/font.png.

The font sheet is one row of fixed-size cells; font.json lists the cell size
and which character sits in each cell. Text is always upper case.
"""

import json
import os

import pygame

from game import settings as S


class BitmapFont:
    def __init__(self, name="font"):
        base = S.resource_path(os.path.join("assets", "ui", name))
        sheet = pygame.image.load(base + ".png").convert_alpha()
        with open(base + ".json", encoding="utf-8") as f:
            meta = json.load(f)
        self.cw, self.ch = meta["cell"]
        self.glyphs, self.shadows = {}, {}
        for i, char in enumerate(meta["chars"]):
            glyph = sheet.subsurface((i * self.cw, 0, self.cw, self.ch)).copy()
            shadow = glyph.copy()
            shadow.fill(
                (0, 0, 0), special_flags=pygame.BLEND_RGB_MULT
            )  # black, same shape
            self.glyphs[char], self.shadows[char] = glyph, shadow

    def width(self, line):
        return max(0, len(line) * self.cw - 1)

    def draw(self, surf, text, pos, align="center", shadow=True):
        """Draw text at pos. align: "center" (pos is the top-centre) or "left".
        Use \\n for several lines."""
        x0, y = pos
        for line in text.upper().split("\n"):
            x = x0 - self.width(line) // 2 if align == "center" else x0
            for char in line:
                if char not in self.glyphs:
                    char = "?"
                if shadow:
                    surf.blit(self.shadows[char], (x + 1, y + 1))
                surf.blit(self.glyphs[char], (x, y))
                x += self.cw
            y += self.ch + 2
