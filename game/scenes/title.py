"""Title screen. Placeholder text for now; the character art comes in step 3."""

from game import controls
from game import settings as S
from game.gfx.text import BitmapFont
from game.scenes.base import Scene


class TitleScene(Scene):
    def __init__(self):
        self.font = BitmapFont()
        self.time = 0.0

    def handle_event(self, event):
        if not self.app:
            return
        if controls.pressed(event, controls.CONFIRM):
            from game.scenes.match import (
                Match,  # imported here to avoid a circular import
            )

            # Until the level select (step 3): play the next level you haven't beaten.
            self.app.switch(Match(self.app.progress.next_to_play()))
        elif controls.pressed(event, controls.BACK):
            self.app.quit()

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        surf.fill(S.COL_BG)
        self.font.draw(surf, S.TITLE, (S.WIDTH // 2, 80))
        if int(self.time * 2) % 2 == 0:  # blink twice a second
            self.font.draw(surf, "Press Enter", (S.WIDTH // 2, 130))
        self.font.draw(surf, "Esc to quit", (S.WIDTH // 2, 200), color=S.COL_MENU_DIM)
