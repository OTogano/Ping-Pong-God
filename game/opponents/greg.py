"""Coach Greg (Tutorial): now and then a belly bump instead of a swing.

The belly bump is just for show: it never changes where the ball goes.
"""

import random

from game.audio import sfx
from game.opponents.base import Opponent

BELLY_CHANCE = 0.2  # 1 in 5 centre shots


class Greg(Opponent):
    serve_sound = "greg_whistle"

    def choose_trick(self):
        if self.m.target in (1, 2) and random.random() < BELLY_CHANCE:
            return "belly"
        return None

    def windup_tag(self):
        return "windup_belly" if self.trick == "belly" else super().windup_tag()

    def hit(self):
        if self.trick == "belly":
            self.m.opp_anim.play("belly")
            sfx.play("greg_belly")
            return True
        return False
