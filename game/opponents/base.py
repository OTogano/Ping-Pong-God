"""Opponent: what every opponent does, and the hooks the match calls.

The match (game/scenes/match.py) runs the rally. At key moments it asks the
opponent what to do, so each opponent's file can add tricks without touching
the match. Every hook below does "nothing special" here; an opponent overrides
only the ones it needs.

    choose_trick()     a windup is starting: name this shot's trick (or None)
    windup(after)      set up the windup yourself? (return True if you set the phase)
    windup_tag()       the windup animation      windup_extra(): extra windup seconds
    hit()              the ball is hit: return True if you played your own animation
    after_hit()        the incoming flight has started (its duration is known)
    flight(f)          every frame of an incoming ball, f = 0..1 of the way
    advance(phase)     a phase of your own just ended (juggle, portal, rewind...): True if handled
    returned()         the player hit it back
    point_over(won)    someone just scored (won: True if it was the player)
    match_over(won)    the match is over
    press(lane)        a hit key was pressed: return True if you used it (Squidy's grab)
    update(dt)         every frame
    draw_stage(surf)   drawn behind the props (lightning in the sky)
    draw_effects(surf) drawn over the player (tentacles, portals, illusions)

The match's state the hooks use: m.phase, m.t, m.duration, m.flight, m.bend,
m.arc_from, m.target, m.opp_pos, m.speed, m.ball, m.trail, m.trail_colours,
m.message, m.player_pos, m.player_score, m.opp_score, m.opp_anim, m.level,
m.stage_time, and m.set_phase(), m.begin_windup(), m.point().
"""

import random

from game import settings as S


class Opponent:
    behind_table = True  # drawn behind the table (False: over its far end)
    early_phases = ("incoming",)  # pressing during these phases is "Too early!"
    flight_phases = ()  # extra phases in which the ball flies along m.flight
    serve_sound = None  # played as each point starts (Greg's whistle)
    intro_sound = None  # played once as the match starts

    def __init__(self, match):
        self.m = match
        self.trick = None  # this shot's trick (each opponent names its own), or None
        self.trick_done = False  # has a mid-flight trick happened yet?

    # ---------------------------------------------------------------- where they stand
    def feet(self, pos):
        """Where they stand at spot `pos` (bottom-centre of the sprite)."""
        return S.OPPONENT_FEET[pos]

    def move_to(self, pos, duration):
        """Go to spot `pos`. Most opponents just appear there; floaters and robots travel."""
        self.m.opp_pos = pos

    def draw_pos(self):
        """Where to draw them right now."""
        return self.feet(self.m.opp_pos)

    # ---------------------------------------------------------------- tricks
    @staticmethod
    def pick(options) -> str | None:
        """At most one trick per shot. options: [(name, chance), ...] -> a name or None."""
        r = random.random()
        for name, chance in options:
            if r < chance:
                return name
            r -= chance
        return None

    def choose_trick(self) -> str | None:
        return None

    def windup(self, after_trick) -> bool:
        return False

    def windup_tag(self) -> str:
        """Opponents who never move (Captain Squidy) wind up the paddle that will hit."""
        lane_tag = f"windup_{'dfjk'[self.m.opp_pos]}"
        return lane_tag if self.m.opp_anim.has(lane_tag) else "windup"

    def windup_extra(self) -> float:
        return 0.0

    def hit(self) -> bool:
        return False

    def after_hit(self):
        pass

    def flight(self, f):
        pass

    def advance(self, phase) -> bool:
        return False

    def returned(self):
        pass

    def point_over(self, player_won):
        pass

    def match_over(self, player_won):
        pass

    def reset(self):
        """A new point is starting."""
        self.trick = None

    def press(self, lane) -> bool:
        return False

    # ---------------------------------------------------------------- the ball
    def ball_visible(self) -> bool:
        """False while the ball is somewhere you can't see it (in a portal, in a cannon)."""
        return True

    def ball_hidden(self) -> bool:
        """True to hide the ball but keep its shadow (BOT's invisible ball)."""
        return False

    def player_offset(self) -> int:
        """Nudge the player's sprite (Squidy shakes you in his grip)."""
        return 0

    # ---------------------------------------------------------------- every frame
    def update(self, dt):
        pass

    def draw_stage(self, surf):
        pass

    def draw_effects(self, surf):
        pass
