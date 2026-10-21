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
        # The font is drawn in a single colour; remember it so draw() can swap it.
        self.base_color = next(
            sheet.get_at((x, y))
            for x in range(sheet.get_width())
            for y in range(sheet.get_height())
            if sheet.get_at((x, y)).a
        )
        self._coloured = {}  # (char, colour) -> recoloured glyph, made on first use

    def _glyph(self, char, color):
        if color is None:
            return self.glyphs[char]
        key = (char, color)
        if key not in self._coloured:
            glyph = self.glyphs[char].copy()
            pixels = pygame.PixelArray(glyph)
            pixels.replace(self.base_color, pygame.Color(color))
            del pixels
            self._coloured[key] = glyph
        return self._coloured[key]

    def width(self, line):
        return max(0, len(line) * self.cw - 1)

    def draw(self, surf, text, pos, align="center", shadow=True, color=None):
        """Draw text at pos. align: "center" (pos is the top-centre) or "left".
        Use \\n for several lines. color: e.g. "#7C7C7C" (default: the font's own)."""
        x0, y = pos
        for line in text.upper().split("\n"):
            x = x0 - self.width(line) // 2 if align == "center" else x0
            for char in line:
                if char not in self.glyphs:
                    char = "?"
                if shadow:
                    surf.blit(self.shadows[char], (x + 1, y + 1))
                surf.blit(self._glyph(char, color), (x, y))
                x += self.cw
            y += self.ch + 2
