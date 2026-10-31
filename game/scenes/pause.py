"""Pause menu, opened with Esc during a match. Drawn over the frozen match."""

import pygame

from game import controls, save
from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.text import BitmapFont
from game.gfx.ui import Menu, dim, panel
from game.scenes.base import Scene


class PauseScene(Scene):
    is_overlay = True

    def __init__(self, restart, level_select, crt_available):
        """restart / level_select: functions to call for those options.
        crt_available: False on the software renderer, which has no CRT shader."""
        self.font = BitmapFont()
        items = [
            ("Resume", self.resume),
            ("Restart", restart),
            (lambda: f"Sound: {'off' if sfx.muted else 'on'}", self.toggle_sound),
        ]
        if crt_available:
            items.append(
                (lambda: f"CRT filter: {'on' if fx.crt else 'off'}", self.toggle_crt)
            )
        items.append(("Level select", level_select))
        self.menu = Menu(items)

    def resume(self):
        if self.app:
            sfx.unpause()
            self.app.pop()

    def toggle_sound(self):
        sfx.toggle_mute()
        if self.app:  # remembered between sessions
            self.app.progress.muted = sfx.muted
            save.save(self.app.progress)

    @staticmethod
    def toggle_crt():
        fx.crt = not fx.crt

    def handle_event(self, event):
        if controls.pressed(event, controls.BACK):
            self.resume()
        else:
            self.menu.handle_event(event)

    def draw(self, surf):
        dim(surf)
        box = pygame.Rect(0, 0, 150, 30 + len(self.menu.items) * S.MENU_LINE)
        box.center = (S.WIDTH // 2, S.HEIGHT // 2)
        panel(surf, box)
        self.font.draw(surf, "Paused", (box.centerx, box.top + 8))
        self.menu.draw(surf, self.font, box.centerx, box.top + 24)
