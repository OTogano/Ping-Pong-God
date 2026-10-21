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
from game.gfx.sprites import Animator, load_animations, recolour


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pt(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


class Match:
    def __init__(self):
        self.font = pygame.font.Font(None, 16)
        anims = load_animations("player")
        self.player_anim = Animator(anims)
        self.opp_anim = Animator(recolour(anims, S.OPPONENT_KIT))
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = None  # shown briefly after a miss so you learn the rule
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
        self.opp_pos = random.randrange(4)
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self._set_phase("return", S.RETURN_TIME)

    def _point(self, player_won, message):
        if player_won:
            self.player_score += 1
        else:
            self.opp_score += 1
            self.last_target = self.target
        self.message = message
        if S.POINTS_TO_WIN in (self.player_score, self.opp_score):
            winner = "You win!" if player_won else "You lose!"
            self.message = f"{message}  {winner}  (R to restart)"
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
        self.player_anim.play(f"swing_{'dfjk'[pressed]}")

        if self.phase == "incoming" and S.EARLY_PRESS_IS_MISS:
            self._point(False, "Too early!")
        elif self.phase == "window":
            if pressed == self.target:
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
        self._draw_table(surf)
        if self.last_target is not None:
            # After a miss, outline the correct spot so the rule is learnable.
            x, y = S.PLAYER_STAND[self.last_target]
            half = S.SPRITE_SIZE // 2
            pygame.draw.rect(
                surf,
                S.COL_HIGHLIGHT,
                (x - half, y - half, S.SPRITE_SIZE, S.SPRITE_SIZE),
                1,
            )
        # Opponent first so the ball and player draw over them.
        self._draw_sprite(surf, self.opp_anim.image, S.OPPONENT_STAND[self.opp_pos])
        self._draw_sprite(surf, self.player_anim.image, S.PLAYER_STAND[self.player_pos])
        self._draw_ball(surf)
        self._draw_hud(surf)

    def _draw_table(self, surf):
        x, y, w, h = S.TABLE
        pygame.draw.rect(surf, S.COL_TABLE, S.TABLE)
        pygame.draw.rect(surf, S.COL_LINES, S.TABLE, 1)
        pygame.draw.line(surf, S.COL_LINES, (x + w // 2, y), (x + w // 2, y + h - 1))
        pygame.draw.line(surf, S.COL_NET, (x - 4, S.NET_Y), (x + w + 3, S.NET_Y), 2)

    def _draw_sprite(self, surf, image, pos):
        """Draw a character's current animation frame centred on pos."""
        surf.blit(image, image.get_rect(center=pos))

    def _draw_ball(self, surf):
        if self.phase in ("point", "over"):
            return
        bx, by = self.ball
        pygame.draw.ellipse(surf, S.COL_SHADOW, (bx - 3, by - 1, 6, 3))
        centre = (round(bx), round(by - self.ball_h))
        pygame.draw.circle(surf, S.COL_BALL_OUTLINE, centre, 3)
        pygame.draw.circle(surf, S.COL_BALL, centre, 2)

    def _draw_hud(self, surf):
        # Scores sit in the left margin: CPU on their half, YOU on yours.
        cpu = self.font.render(f"CPU {self.opp_score}", False, S.COL_TEXT)
        you = self.font.render(f"YOU {self.player_score}", False, S.COL_TEXT)
        surf.blit(cpu, (4, S.NET_Y - 14))
        surf.blit(you, (4, S.NET_Y + 4))
        if self.message:
            msg = self.font.render(self.message, False, S.COL_TEXT)
            surf.blit(msg, msg.get_rect(center=(S.WIDTH // 2, S.NET_Y - 12)))
