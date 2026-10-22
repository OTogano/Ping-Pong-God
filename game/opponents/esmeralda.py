"""Esmeralda (Level 2): the smash. Red eyes and a wicked grin, then a flaming shot
twice as fast. It still lands where her position says."""

import random

from game.gfx.effects import fx
from game.opponents.base import Opponent

SMASH_CHANCE = 0.35
SMASH_AFTER_POINTS = 0  # only after this many points have been played (0 = any time)
SMASH_SPEED = 2.0  # the ball flies twice as fast
SMASH_TELL = 0.2  # her tell (windup_smash) lasts this much longer than a normal windup
SMASH_FLASH = 0.45  # orange flash, big shake and a shockwave
SMASH_FLASH_COLOR = "#F83800"
SMASH_SHAKE = (4, 0.35)
SMASH_RIPPLE_TIME = 0.6
COL_FLAMES = ["#F83800", "#E45C10", "#AC7C00"]  # hot to cool


class Esmeralda(Opponent):
    def choose_trick(self):
        played = self.m.player_score + self.m.opp_score
        if played >= SMASH_AFTER_POINTS and random.random() < SMASH_CHANCE:
            return "smash"
        return None

    def windup(self, after_trick):
        if self.trick != "smash":
            return False
        m = self.m
        m.trail = []  # forget the last smash's flames (they were at your end)
        m.opp_anim.switch("windup_smash")
        m.set_phase("windup", m.level.windup_time + SMASH_TELL)
        return True

    def hit(self):
        if self.trick != "smash":
            return False
        m = self.m
        m.opp_anim.play("smash")
        x, y = m.flight[0]
        fx.flash(SMASH_FLASH, color=SMASH_FLASH_COLOR)
        fx.shake(*SMASH_SHAKE)
        fx.ripple(x, y, SMASH_RIPPLE_TIME)
        m.speed = SMASH_SPEED
        m.trail, m.trail_colours = [], COL_FLAMES
        return True
