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

from game import settings as S
from game.gfx.effects import fx
from game.gfx.sprites import Animator, load_animations, load_image, load_strip, recolour
from game.gfx.text import BitmapFont
from game.gfx.ui import KeyIcons, Scoreboard


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pt(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


class Match:
    def __init__(self):
        self.font = BitmapFont()
        self.table = load_image("sprites", "table.png")
        self.net = load_image("sprites", "net.png")
        self.ball_img, self.ball_squash, self.ball_shadow = load_strip(
            "sprites/ball.png", S.BALL_SIZE
        )
        self.scoreboard = Scoreboard()
        self.keys = KeyIcons()
        self.returns = 0  # successful returns this match (key hints fade after a few)
        self.squash = 0.0
        anims = load_animations("player")
        self.player_anim = Animator(anims)
        self.opp_anim = Animator(recolour(anims, S.OPPONENT_KIT))
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = None  # shown briefly after a miss so you learn the rule
        # Rally state; _start_point() and _set_phase() fill these in.
        self.phase, self.duration, self.t = "ready", 0.0, 0.0
        self.flight = ((0.0, 0.0), (0.0, 0.0), 0.0)  # (start, end, arc height)
        self._start_point()

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
        self._set_phase("incoming", S.FLY_TIME)

    def _player_returns(self):
        # The opponent moves to their next spot as the ball travels:
        # that movement IS the telegraph for the next shot.
        self.returns += 1
        self.opp_pos = random.randrange(4)
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self._set_phase("return", S.RETURN_TIME)

    def _point(self, player_won, message):
        if player_won:
            self.player_score += 1
        else:
            self.opp_score += 1
            self.last_target = self.target
            fx.shake(*S.MISS_SHAKE)
        self.scoreboard.set(self.opp_score, self.player_score)
        self.message = message
        if S.POINTS_TO_WIN in (self.player_score, self.opp_score):
            winner = "You win!" if player_won else "You lose!"
            self.message = f"{message}\n{winner}\nPress R to restart"
            self._set_phase("over", math.inf)
        else:
            self._set_phase("point", S.POINT_PAUSE)

    def _advance(self):
        if self.phase == "ready":
            self._set_phase("windup", S.WINDUP_TIME)
        elif self.phase == "windup":
            self._opponent_hits()
        elif self.phase == "incoming":
            self.flight = (
                S.PLAYER_BOUNCE[self.target],
                S.PLAYER_HIT[self.target],
                S.WINDOW_ARC,
            )
            self.squash = S.BALL_SQUASH_TIME  # the ball just bounced on your side
            self._set_phase("window", S.HIT_WINDOW)
        elif self.phase == "window":
            self._point(False, "Too late!")
        elif self.phase == "return":
            if random.random() < S.OPPONENT_MISS_CHANCE:
                self._point(True, "Opponent missed!")
            else:
                self._set_phase("windup", S.WINDUP_TIME)
        elif self.phase == "point":
            self._start_point()

    # ------------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_r and self.phase == "over":
            self.__init__()
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
        hints_on = S.KEY_HINTS and (
            S.KEY_HINT_RETURNS is None or self.returns < S.KEY_HINT_RETURNS
        )
        if hints_on and self.phase in ("incoming", "window"):
            return self.target
        if self.last_target is not None:  # after a miss, show which key was right
            return self.last_target
        return None

    def _draw_sprite(self, surf, image, pos):
        """Draw a character's current animation frame centred on pos."""
        surf.blit(image, image.get_rect(center=pos))

    def _ball_visible(self):
        return self.phase not in ("point", "over")

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
