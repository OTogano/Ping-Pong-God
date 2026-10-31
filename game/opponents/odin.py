"""The Ping Pong God, ♑□♎ (Final): floats between spots above the far end of the
table, and every hit lands like thunder. His tricks unlock as the match goes on:

  Redirect  (from the start) - his hand sweeps toward another lane and the ball bends there.
  Illusions (from 2 points)  - fake balls fly with the real one. Fakes cast no shadow.
  Rewind    (from 5 points)  - time runs backwards: the ball flies back to him, he floats
                               to a new spot and answers with a spike.

His stage has a storm: lightning strikes in the sky now and then.
"""

import math
import random

import pygame

from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.geometry import lerp_pt
from game.opponents.base import Opponent

FEET = (
    (56, 86),
    (104, 62),
    (152, 62),
    (200, 86),
)  # his four spots: hovering over the far end
REDIRECT_CHANCE = 0.25
ILLUSION_CHANCE, ILLUSION_AFTER = (
    0.25,
    2,
)  # tricks unlock once either score reaches *_AFTER
REWIND_CHANCE, REWIND_AFTER = 0.2, 5
ILLUSION_COUNT = (2, 3)  # how many fake balls
ILLUSION_SPEEDS = (
    0.55,
    1.3,
)  # fakes fly this many times as long as the real ball (random in range)
REDIRECT_AT = 0.3  # how far through the flight his hand bends the ball (0..1)
REDIRECT_EXTRA = (
    0.1  # the bent flight takes this much longer than what was left of the old one
)
REWIND_AT = 0.5  # how far through the flight time turns back
REWIND_TIME = 0.7  # how long the ball takes to fly back to him
SPIKE_SPEED = 1.8  # after a rewind: the spike flies this many times faster
SPIKE_TELL = 0.15  # ...after a windup this much longer
SPIKE_FLASH = 0.5
SPIKE_SHAKE = (5, 0.4)
SPIKE_RIPPLE_TIME = 0.7
POWER_SHAKE = (2, 0.15)  # every one of his hits shakes the screen...
POWER_RIPPLE_TIME = 0.45  # ...and sends out a shockwave
COL_POWER_TRAIL = [
    "#BCBCBC",
    "#0078F8",
    "#4428BC",
]  # his ball's glowing trail, bright to dark
COL_DIVINE = "#0078F8"  # flash when he bends the ball, sparkles of vanishing illusions
LIGHTNING_CHANCE = 0.15  # strikes per second (on average)
LIGHTNING_TIME = 0.15  # how long a bolt stays on screen
LIGHTNING_FLASH = 0.18  # screen flash (skipped while a ball is coming at you)
COL_LIGHTNING = "#BCBCBC"
COL_LIGHTNING_GLOW = "#6844FC"


class Odin(Opponent):
    behind_table = False  # he floats above the far end of the table
    flight_phases = ("rewind",)

    def __init__(self, match):
        super().__init__(match)
        self.glide_from = self.feet(S.SERVE_POSITION)
        self.glide_t = self.glide_time = 0.0
        self.spike = False  # his answer after a rewind
        self.illusions = []  # fake balls: [start, end, duration, time so far]
        self.pops = []  # where illusions vanished: [x, y, time left]
        self.bolt = []  # lightning bolt points while one is on screen
        self.bolt_t = 0.0

    # ---------------------------------------------------------------- floating
    def feet(self, pos):
        return FEET[pos]

    def move_to(self, pos, duration):
        self.glide_from = self.draw_pos()
        self.m.opp_pos = pos
        self.glide_t, self.glide_time = 0.0, duration

    def draw_pos(self):
        """Gliding (easing in and out) and bobbing in the air."""
        to = self.feet(self.m.opp_pos)
        k = min(self.glide_t / self.glide_time, 1.0) if self.glide_time > 0 else 1.0
        k = k * k * (3 - 2 * k)
        x, y = lerp_pt(self.glide_from, to, k)
        return (x, y + (1 - math.cos(self.m.stage_time * 3)) * 1.5)

    # ---------------------------------------------------------------- tricks
    def reset(self):
        super().reset()
        self.spike = False
        self.illusions = []

    def choose_trick(self):
        lead = max(self.m.player_score, self.m.opp_score)
        options = [("redirect", REDIRECT_CHANCE)]
        if lead >= ILLUSION_AFTER:
            options.append(("illusion", ILLUSION_CHANCE))
        if lead >= REWIND_AFTER:
            options.append(("rewind", REWIND_CHANCE))
        return self.pick(options)

    def windup_extra(self):
        return SPIKE_TELL if self.spike else 0.0  # a beat longer before the spike

    def hit(self):
        """Every hit lands like thunder, the spike after a rewind even more so."""
        m = self.m
        x, y = m.flight[0]
        if self.spike:
            sfx.play("god_spike")
            fx.flash(SPIKE_FLASH, color=COL_LIGHTNING)
            fx.shake(*SPIKE_SHAKE)
            fx.ripple(x, y, SPIKE_RIPPLE_TIME)
        else:
            sfx.play("god_hit")
            fx.shake(*POWER_SHAKE)
            fx.ripple(x, y, POWER_RIPPLE_TIME)
        m.trail, m.trail_colours = [], COL_POWER_TRAIL
        if self.trick == "illusion":
            m.opp_anim.play("illusion")
            sfx.play("god_illusion")
            return True
        return False

    def after_hit(self):
        if self.trick != "illusion":
            return
        m = self.m  # fakes to the other lanes, some faster, some slower
        lanes = [p for p in range(4) if p != m.target]
        random.shuffle(lanes)
        start = S.OPPONENT_HIT[m.opp_pos]
        self.illusions = [
            [
                start,
                S.PLAYER_BOUNCE[lane],
                m.duration * random.uniform(*ILLUSION_SPEEDS),
                0.0,
            ]
            for lane in lanes[: random.randint(*ILLUSION_COUNT)]
        ]

    def flight(self, f):
        if self.trick_done:
            return
        if self.trick == "redirect" and f >= REDIRECT_AT:
            self._redirect(f)
        elif self.trick == "rewind" and f >= REWIND_AT:
            self._rewind()

    def _redirect(self, f):
        """His hand sweeps toward another lane and the ball bends there. Follow the hand!"""
        m = self.m
        self.trick_done = True
        start, end, _ = m.flight
        new = random.choice([p for p in range(4) if p != m.target])
        m.target = new
        m.opp_anim.play(f"redirect_{'dfjk'[new]}")
        sfx.play("god_redirect")
        fx.flash(0.15, color=COL_DIVINE)
        here = m.ball
        ahead = lerp_pt(
            start, end, min(f + 0.3, 1.0)
        )  # it carries on the old way for a moment, then curves
        m.set_phase("incoming", m.duration - m.t + REDIRECT_EXTRA)
        m.flight = (here, S.PLAYER_BOUNCE[new], S.BALL_ARC)
        m.bend, m.arc_from = ahead, f

    def _rewind(self):
        """Time runs backwards: the ball flies back to him while he floats to a new spot."""
        m = self.m
        self.trick_done = True
        self.illusions = []
        m.opp_anim.play("rewind")
        sfx.play("god_rewind")
        new = random.choice([p for p in range(4) if p != m.opp_pos])
        self.move_to(new, REWIND_TIME)
        m.flight = (m.ball, S.OPPONENT_HIT[new], S.BALL_ARC)
        fx.rewind(REWIND_TIME)
        m.set_phase("rewind", REWIND_TIME)

    def advance(self, phase):
        if phase != "rewind":
            return False
        self.spike = True  # winds up at his new spot: a spike
        self.m.speed = SPIKE_SPEED
        self.m.begin_windup(after_trick=True)
        return True

    def _vanish_illusions(self):
        for start, end, dur, t in self.illusions:
            self.pops.append([*lerp_pt(start, end, min(t / dur, 1.0)), 0.2])
        self.illusions = []

    def returned(self):
        self.spike = False
        self._vanish_illusions()

    def point_over(self, player_won):
        self._vanish_illusions()

    # ---------------------------------------------------------------- every frame
    def update(self, dt):
        self.glide_t += dt
        for ill in self.illusions:
            ill[3] += dt
        for ill in [
            i for i in self.illusions if i[3] >= i[2]
        ]:  # a fake reaches the table: it vanishes
            self.illusions.remove(ill)
            self.pops.append([*ill[1], 0.2])
        for pop in self.pops:
            pop[2] -= dt
        self.pops = [p for p in self.pops if p[2] > 0]
        self._storm(dt)

    def _storm(self, dt):
        """Now and then lightning strikes in the sky beside the island."""
        self.bolt_t = max(0.0, self.bolt_t - dt)
        if self.bolt_t > 0 or random.random() >= LIGHTNING_CHANCE * dt:
            return
        x = random.choice(
            (random.randint(6, 24), random.randint(232, 250))
        )  # left or right of the island
        y, self.bolt = 0, [(x, 0)]
        while y < random.randint(80, 200):  # zig-zag down
            y += random.randint(6, 14)
            x = min(max(x + random.randint(-5, 5), 2), S.WIDTH - 3)
            self.bolt.append((x, y))
        self.bolt_t = LIGHTNING_TIME
        if self.m.phase not in (
            "incoming",
            "window",
        ):  # never blind you while the ball is coming
            fx.flash(LIGHTNING_FLASH, 0.1, color=COL_LIGHTNING)

    def draw_stage(self, surf):
        if self.bolt_t > 0 and len(self.bolt) > 1:
            pygame.draw.lines(surf, COL_LIGHTNING_GLOW, False, self.bolt, 3)
            pygame.draw.lines(surf, COL_LIGHTNING, False, self.bolt, 1)

    def draw_effects(self, surf):
        """Fake balls look exactly like the real one, except they cast no shadow."""
        ball = self.m.ball_img
        for start, end, dur, t in self.illusions:
            f = min(t / dur, 1.0)
            x, y = lerp_pt(start, end, f)
            h = math.sin(math.pi * f) * S.BALL_ARC
            surf.blit(ball, ball.get_rect(center=(round(x), round(y - h))))
        for x, y, left in self.pops:  # vanishing: a burst of sparkles
            r = round((0.2 - left) * 30) + 1
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                surf.set_at((round(x) + dx, round(y) + dy), COL_DIVINE)
