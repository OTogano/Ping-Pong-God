"""Title screen: the character close-up, the logo and "Press Enter"."""

from game import controls
from game import settings as S
from game.audio import sfx
from game.gfx.sprites import load_image
from game.gfx.text import BitmapFont
from game.scenes.base import Scene


class TitleScene(Scene):
    def __init__(self):
        self.font = BitmapFont()
        self.background = load_image("ui", "title_bg.png")
        self.logo = load_image("ui", "logo.png")
        self.time = 0.0

    def handle_event(self, event):
        if not self.app:
            return
        if controls.pressed(event, controls.CONFIRM):
            sfx.play("menu_select")
            from game.scenes.level_select import (
                LevelSelectScene,  # avoids a circular import
            )

            self.app.switch(LevelSelectScene(self.app.progress.next_to_play()))
        elif controls.pressed(event, controls.BACK):
            self.app.quit()

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        surf.blit(self.background, (0, 0))
        surf.blit(self.logo, self.logo.get_rect(midtop=(S.WIDTH // 2, 10)))
        if int(self.time * 2) % 2 == 0:  # blink twice a second
            self.font.draw(surf, "Press Enter", (S.WIDTH // 2, 68))
        self.font.draw(
            surf, "Esc: quit", (4, S.HEIGHT - 10), align="left", color=S.COL_MENU_DIM
        )
