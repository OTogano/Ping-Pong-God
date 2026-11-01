"""The game loop and the scene stack.

Scenes are kept in a stack. Only the top scene gets input and updates.
Drawing starts from the last full-screen scene, so an overlay such as the
pause menu is drawn on top of the frozen match below it.

    app.switch(scene)  - replace everything (e.g. title -> match)
    app.push(scene)    - open an overlay on top (e.g. pause)
    app.pop()          - close the top overlay
"""

import sys

import pygame

from game import save
from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.renderer import create_renderer


class App:
    def __init__(self):
        pygame.mixer.pre_init(*S.MIXER)
        pygame.init()
        sfx.init()
        pygame.display.set_caption(S.TITLE)
        self.renderer = create_renderer((S.WIDTH * S.SCALE, S.HEIGHT * S.SCALE))
        print(f"Renderer: {self.renderer.name}")
        # We draw everything on this small canvas; the renderer scales it up
        # to the window and applies the shader effects.
        self.canvas = pygame.Surface((S.WIDTH, S.HEIGHT))
        self.clock = pygame.time.Clock()
        self.stack = []
        self.progress = save.load()  # which levels are beaten / unlocked
        sfx.muted = self.progress.muted

    # ---------------------------------------------------------------- scenes
    def _attach(self, scene):
        scene.app = self
        return scene

    def switch(self, scene):
        self.stack = [self._attach(scene)]

    def push(self, scene):
        self.stack.append(self._attach(scene))

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()

    @property
    def top(self):
        return self.stack[-1]

    @staticmethod
    def quit():
        pygame.quit()
        sys.exit()

    # ---------------------------------------------------------------- loop
    def run(self, first_scene):
        self.switch(first_scene)
        while True:
            dt = min(
                self.clock.tick(S.FPS) / 1000, 0.05
            )  # cap dt so a lag spike can't skip a hit window

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                self.top.handle_event(event)

            self.top.update(dt)
            sfx.update(dt)  # starts the next music track once the old one has faded
            fx.update(dt)

            # Draw from the last full-screen scene up, so overlays sit on top.
            start = len(self.stack) - 1
            while start > 0 and self.stack[start].is_overlay:
                start -= 1
            for scene in self.stack[start:]:
                scene.draw(self.canvas)

            self.renderer.present(self.canvas)
