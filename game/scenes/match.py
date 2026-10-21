"""One match: the rally state machine, input and placeholder drawing.

The rally is a loop of phases:

    ready -> windup -> incoming -> window -> return -> windup -> ...
                                     |                   |
                                     +-> point (miss)    +-> point (opponent misses)

Each phase has a duration; `self.t` counts up through it. When it reaches the
duration, `_advance()` moves to the next phase.
"""

import math
import random

import pygame

from game import controls
from game import settings as S
from game.gfx.effects import fx
from game.gfx.sprites import Animator, load_animations, load_image, load_strip, recolour
from game.gfx.text import BitmapFont
from game.gfx.ui import KeyIcons, Scoreboard
from game.levels import LEVELS
from game.scenes.base import Scene
from game.scenes.level_select import LevelSelectScene
from game.scenes.pause import PauseScene
from game.scenes.result import ResultScene


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pt(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


class Match(Scene):
    def __init__(self, level_index=0):
        self.level_index = level_index
        self.level = LEVELS[level_index]
        self.font = BitmapFont()
        self.table = load_image("sprites", "table.png")
        self.net = load_image("sprites", "net.png")
        self.ball_img, self.ball_squash, self.ball_shadow = load_strip(
            "sprites/ball.png", S.BALL_SIZE
        )
        self.scoreboard = Scoreboard()
        self.keys = KeyIcons()
        self.squash = 0.0
        anims = load_animations("player")
        self.player_anim = Animator(anims)
        self.opp_anim = Animator(recolour(anims, self.level.kit))
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = None  # shown briefly after a miss so you learn the rule
        # Rally state; _start_point() and _set_phase() fill these in.
        self.phase, self.duration, self.t = "ready", 0.0, 0.0
        self.flight = ((0.0, 0.0), (0.0, 0.0), 0.0)  # (start, end, arc height)
        self.won = self.unlocked = False  # set when the match ends
        self._start_point()
        # First serve: show the level name and wait a little longer.
        self.message = f"{self.level.name}\nvs {self.level.opponent}"
        self.duration = S.INTRO_TIME

    # ------------------------------------------------------------------ phases
    def _set_phase(self, name, duration):
        self.phase = name
        self.duration = duration
        self.t = 0.0

    def _start_point(self):
        self.opp_pos = S.SERVE_POSITION
        self.target = S.LANDING_FOR[self.opp_pos]
        self.ball = S.OPPONENT_HIT[self.opp_pos]
        self.ball_h = 0
        self.message = ""
        self.last_target = None
        self._set_phase("ready", S.READY_TIME)

    def _opponent_hits(self):
        self.target = S.LANDING_FOR[self.opp_pos]
        self.opp_anim.play(f"swing_{'dfjk'[self.opp_pos]}")
        self.flight = (
            S.OPPONENT_HIT[self.opp_pos],
            S.PLAYER_BOUNCE[self.target],
            S.BALL_ARC,
        )
        self._set_phase("incoming", self.level.fly_time)

    def _player_returns(self):
        # The opponent moves to their next spot as the ball travels:
        # that movement IS the telegraph for the next shot.
        self.opp_pos = random.randrange(4)
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self._set_phase("return", self.level.return_time)

    def _point(self, player_won, message):
        if player_won:
            self.player_score += 1
        else:
            self.opp_score += 1
            self.last_target = self.target
            fx.shake(*S.MISS_SHAKE)
        self.scoreboard.set(self.opp_score, self.player_score)
        self.message = message
        if self.level.points_to_win in (self.player_score, self.opp_score):
            self.won = player_won
            self.message = f"{message}\n{'You win!' if player_won else 'You lose!'}"
            if player_won and self.app:
                self.unlocked = self.app.progress.mark_won(self.level_index)
            self._set_phase("over", S.RESULT_DELAY)
        else:
            self._set_phase("point", S.POINT_PAUSE)

    def _advance(self):
        if self.phase == "ready":
            self.message = ""  # clears the level name after the first serve
            self._set_phase("windup", self.level.windup_time)
        elif self.phase == "windup":
            self._opponent_hits()
        elif self.phase == "incoming":
            self.flight = (
                S.PLAYER_BOUNCE[self.target],
                S.PLAYER_HIT[self.target],
                S.WINDOW_ARC,
            )
            self.squash = S.BALL_SQUASH_TIME  # the ball just bounced on your side
            self._set_phase("window", self.level.hit_window)
        elif self.phase == "window":
            self._point(False, "Too late!")
        elif self.phase == "return":
            if random.random() < self.level.opponent_miss_chance:
                self._point(True, "Opponent missed!")
            else:
                self._set_phase("windup", self.level.windup_time)
        elif self.phase == "point":
            self._start_point()
        elif self.phase == "over":
            self._show_result()

    def _show_result(self):
        self._set_phase("done", math.inf)
        if not self.app:
            return
        last = self.level_index == len(LEVELS) - 1
        self.app.push(
            ResultScene(
                won=self.won,
                score=f"You {self.player_score} - {self.opp_score} {self.level.opponent}",
                retry=self.restart,
                level_select=self.level_select,
                next_level=None if last else self.next_level,
                unlocked=LEVELS[self.level_index + 1].name if self.unlocked else None,
                champion=self.won and last,
            )
        )

    # ------------------------------------------------------------------ input
    def restart(self):
        if self.app:
            self.app.switch(Match(self.level_index))

    def next_level(self):
        if self.app:
            self.app.switch(Match(self.level_index + 1))

    def level_select(self):
        if self.app:
            self.app.switch(LevelSelectScene(self.level_index))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if controls.pressed(event, controls.BACK) and self.app:
            self.app.push(
                PauseScene(
                    self.restart, self.level_select, self.app.renderer.supports_crt
                )
            )
            return
        if event.key not in S.HIT_KEYS:
            return

        pressed = S.HIT_KEYS.index(event.key)
        # The player sprite always jumps to the pressed spot and swings,
        # even on a miss, so the controls feel responsive.
        self.player_pos = pressed
        self.keys.press(pressed)
        self.player_anim.play(f"swing_{'dfjk'[pressed]}")

        if self.phase == "incoming" and S.EARLY_PRESS_IS_MISS:
            self._point(False, "Too early!")
        elif self.phase == "window":
            if pressed == self.target:
                fx.flash(S.RETURN_FLASH)
                self._player_returns()
            else:
                self._point(False, "Wrong side!")

    # ------------------------------------------------------------------ update
    def update(self, dt):
        # Crouch in the "ready" pose while the ball is yours to hit.
        self.player_anim.loop(
            "ready" if self.phase in ("incoming", "window") else "idle"
        )
        self.player_anim.update(dt)
        self.opp_anim.update(dt)
        self.scoreboard.update(dt)
        self.keys.update(dt)
        self.squash = max(0.0, self.squash - dt)
        self.t += dt

        if self.phase in ("incoming", "window", "return"):
            start, end, arc = self.flight
            f = min(self.t / self.duration, 1.0)
            self.ball = lerp_pt(start, end, f)
            self.ball_h = math.sin(math.pi * f) * arc  # simple hop: up then down
        elif self.phase in ("ready", "windup"):
            self.ball = S.OPPONENT_HIT[self.opp_pos]
            self.ball_h = 0

        if self.t >= self.duration:
            self._advance()

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        surf.fill(S.COL_FLOOR)
        surf.blit(self.table, S.TABLE_SPRITE_POS)
        self._draw_ball_shadow(surf)
        surf.blit(self.net, S.NET_SPRITE_POS)
        self.scoreboard.draw(surf)
        # After a miss, the correct key stays lit so the rule is learnable.
        self.keys.draw(surf, lit=self._hint_key())
        # Opponent first so the ball and player draw over them.
        self._draw_sprite(surf, self.opp_anim.image, S.OPPONENT_STAND[self.opp_pos])
        self._draw_sprite(surf, self.player_anim.image, S.PLAYER_STAND[self.player_pos])
        self._draw_ball(surf)
        if self.message:
            self.font.draw(surf, self.message, (S.WIDTH // 2, S.MESSAGE_Y))

    def _hint_key(self):
        """Which key icon to light up: the right answer for the incoming shot."""
        # Hints stay on until you've won enough points (tutorial: your first point).
        hints_on = self.player_score < self.level.hints_until_score
        if hints_on and self.phase in ("incoming", "window"):
            return self.target
        if self.last_target is not None:  # after a miss, show which key was right
            return self.last_target
        return None

    def _draw_sprite(self, surf, image, pos):
        """Draw a character's current animation frame centred on pos."""
        surf.blit(image, image.get_rect(center=pos))

    def _ball_visible(self):
        return self.phase not in ("point", "over", "done")

    def _draw_ball_shadow(self, surf):
        if self._ball_visible():
            bx, by = self.ball
            surf.blit(
                self.ball_shadow,
                self.ball_shadow.get_rect(center=(round(bx), round(by))),
            )

    def _draw_ball(self, surf):
        if not self._ball_visible():
            return
        bx, by = self.ball
        image = self.ball_squash if self.squash > 0 else self.ball_img
        surf.blit(image, image.get_rect(center=(round(bx), round(by - self.ball_h))))
