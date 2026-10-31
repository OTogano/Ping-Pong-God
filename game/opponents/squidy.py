"""Captain Squidy (Level 3): fills all four lanes, so his windup shows which paddle
will hit. Two tricks:

  Juggle - he bats the ball between his paddles, then the LAST paddle to touch it
           winds up and fires a fast shot (track the ball!).
  Grab   - a tentacle holds you during his windup. The right key breaks free
           (that press never counts as early), then press again to hit.
"""

import math
import random

import pygame

from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.geometry import bezier
from game.opponents.base import Opponent

ANCHOR = (128, 80)  # he never moves: always drawn here (bottom-centre of his frame)
JUGGLE_CHANCE = 0.3
JUGGLE_HOPS = (3, 5)  # how many hops between paddles (min, max)
HOP_TIME = 0.2  # seconds per hop
JUGGLE_SPEED = 1.6  # the shot after a juggle flies 60% faster
JUGGLE_ARC = 14  # height of each hop
GRAB_CHANCE = 0.25
GRAB_TELL = 0.35  # the windup lasts this much longer while a tentacle reaches for you
GRAB_REACH = 0.3  # time for the tentacle to reach you
GRAB_RETRACT = 0.25  # time for it to slither back when it lets go
COL_TENTACLE = "#940084"
COL_TENTACLE_LIGHT = "#D800CC"
COL_SUCKER = "#E40058"


class Squidy(Opponent):
    behind_table = False  # he leans over the far end of the table
    flight_phases = ("juggle",)

    def __init__(self, match):
        super().__init__(match)
        self.juggle_path = []  # paddles the ball still has to hop between
        self.extra = 0.0  # extra windup time this shot (the grab)
        self.grab = False  # is a tentacle holding the player?
        self.grab_t = 0.0  # time since the grab started
        self.grab_out = (
            0.0  # time left for the tentacle to slither back after letting go
        )
        self.grab_lane = 0  # where the player was grabbed

    def draw_pos(self):
        return ANCHOR

    def reset(self):
        super().reset()
        self.juggle_path = []
        self.grab = False
        self.grab_out = 0.0

    # ---------------------------------------------------------------- juggle
    def choose_trick(self):
        return "juggle" if random.random() < JUGGLE_CHANCE else None

    def windup(self, after_trick):
        self.extra = 0.0
        if self.trick == "juggle":
            path = [self.m.opp_pos]
            for _ in range(random.randint(*JUGGLE_HOPS)):
                path.append(random.choice([p for p in range(4) if p != path[-1]]))
            self.juggle_path = path
            sfx.play("squidy_laugh")
            self._hop()
            return True
        if not after_trick and random.random() < GRAB_CHANCE:
            self._start_grab()
            self.extra = GRAB_TELL  # time to see the tentacle coming
        return False

    def windup_extra(self):
        return self.extra

    def _hop(self):
        m = self.m
        a, b = self.juggle_path[0], self.juggle_path[1]
        m.opp_anim.play(f"bat_{'dfjk'[a]}")
        sfx.play("squidy_tap", fallback="hit")
        m.flight = (S.OPPONENT_HIT[a], S.OPPONENT_HIT[b], JUGGLE_ARC)
        m.set_phase("juggle", HOP_TIME)

    def advance(self, phase):
        if phase != "juggle":
            return False
        self.juggle_path.pop(0)
        if len(self.juggle_path) > 1:
            self._hop()
        else:  # last paddle: wind it up, then a fast shot
            self.m.opp_pos = self.juggle_path.pop()
            self.m.speed = JUGGLE_SPEED
            self.m.begin_windup(after_trick=True)
        return True

    # ---------------------------------------------------------------- grab
    def _start_grab(self):
        self.grab = True
        self.grab_t = 0.0
        self.grab_lane = self.m.player_pos
        self.m.message = "Grabbed!"
        sfx.play("squidy_grab")

    def _release(self):
        if self.grab:
            self.grab = False
            self.grab_out = GRAB_RETRACT
            if self.m.message == "Grabbed!":
                self.m.message = ""

    def press(self, lane):
        m = self.m
        if not (self.grab and m.phase in ("windup", "incoming", "window")):
            return False
        m.keys.press(lane)
        if lane == m.target:  # the right key breaks free
            self._release()
            sfx.play("squidy_free")
            fx.shake(1, 0.1)
        else:
            m.point(False, "Wrong side!")
        return True

    def point_over(self, player_won):
        self._release()
        if not player_won:
            sfx.play("squidy_laugh")  # a haughty laugh at your expense

    def player_offset(self):
        if self.grab and self.grab_t > GRAB_REACH:  # struggling in the tentacle's grip
            return random.choice((-1, 0, 1))
        return 0

    def update(self, dt):
        if self.grab:
            self.grab_t += dt
        self.grab_out = max(0.0, self.grab_out - dt)

    def draw_effects(self, surf):
        """The grabbing tentacle: a tapering Bezier curve from his body to you."""
        if self.grab:
            reach = min(self.grab_t / GRAB_REACH, 1.0)  # stretching out
        elif self.grab_out > 0:
            reach = self.grab_out / GRAB_RETRACT  # slithering back
        else:
            return
        side = -1 if self.grab_lane < 2 else 1  # down the side of the table nearest you
        fx_, fy = S.PLAYER_FEET[self.grab_lane]
        waist = (fx_, fy - 16)
        wob = math.sin(self.m.stage_time * 7) * 3  # it writhes
        cx = S.WIDTH // 2
        p0, p1 = (cx + side * 18, 52), (cx + side * 80, 60 + wob)
        p2, p3 = (cx + side * 92 + wob, waist[1] - 12), waist
        n = 48
        pts = [bezier(p0, p1, p2, p3, i / n) for i in range(round(n * reach) + 1)]
        radius = [
            5 - 2.5 * i / n for i in range(len(pts))
        ]  # thick at the body, thin at the tip
        for (x, y), r in zip(pts, radius):  # black outline first...
            pygame.draw.circle(surf, "#000000", (round(x), round(y)), round(r) + 1)
        for (x, y), r in zip(pts, radius):  # ...then the purple body
            pygame.draw.circle(surf, COL_TENTACLE, (round(x), round(y)), round(r))
        for (x, y), r in zip(pts, radius):  # a light streak along the top
            pygame.draw.circle(
                surf,
                COL_TENTACLE_LIGHT,
                (round(x - r / 2), round(y - r / 2)),
                max(1, round(r / 3)),
            )
        for (x, y), r in list(zip(pts, radius))[3::5]:  # suckers on the underside
            surf.set_at((round(x + r / 2), round(y + r / 2)), COL_SUCKER)
        if reach >= 1 and self.grab:  # coiled around the player's waist
            for dy in (-4, 3):
                band = pygame.Rect(0, 0, 26, 7)
                band.center = (waist[0], waist[1] + dy)
                pygame.draw.ellipse(surf, "#000000", band.inflate(2, 2))
                pygame.draw.ellipse(surf, COL_TENTACLE, band)
                pygame.draw.line(
                    surf,
                    COL_TENTACLE_LIGHT,
                    (band.left + 4, band.top + 1),
                    (band.right - 6, band.top + 1),
                )
                for sx in range(band.left + 4, band.right - 2, 5):
                    surf.set_at((sx, band.bottom - 2), COL_SUCKER)
