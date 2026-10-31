"""BOT (Level 4): a silver robot with an arm cannon. Slides between spots and stops
dead. His tricks all come from the cannon, and unlock after the first point:

  Portal    - a portal opens on your half in the ball's path and another at one of
              his spots. The ball comes out of the exit as if he'd hit it from there.
  Invisible - he zaps the ball as he hits it: only its shadow crosses the table.
  Charge    - from a bottom spot he loads the ball into the cannon, charges for a
              random time, then fires the fastest shot in the game (straight down F or J).
"""

import math
import random

import pygame

from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.geometry import lerp_pt
from game.opponents.base import Opponent

TRICKS_AFTER = 1  # tricks unlock once either score reaches this
PORTAL_CHANCE = 0.25
INVISIBLE_CHANCE = 0.25
CHARGE_CHANCE = 0.3  # only from F or J spots, so it happens a bit less than this
ROBOT_SLIDE = (
    0.6  # slides to his next spot in this share of the move time, then stops dead
)
PORTAL_FIRE_AT = 0.1  # how far into the flight his cannon fires the portals
PORTAL_AT = (
    0.72  # where along the flight the entry portal opens (past the net, on your half)
)
PORTAL_GAP = 0.15  # time the ball spends inside the portal
PORTAL_CLOSE = 0.3  # portals shrink away after the ball comes out
CHARGE_TIME = (0.6, 1.4)  # how long he charges (random, so you can't count it)
CHARGE_FLIGHT = 0.25  # ...and how long the shot takes: the fastest in the game
CHARGE_FLASH = 0.4
CHARGE_SHAKE = (5, 0.35)
CHARGE_RIPPLE_TIME = 0.45
COL_GREEN = "#00B800"  # his light: portals, zaps, the charge
COL_GREEN_DARK = "#007800"
COL_CHARGE_TRAIL = ["#BCBCBC", "#00B800", "#007800"]


class Bot(Opponent):
    intro_sound = "bot_powerup"
    early_phases = (
        "incoming",
        "portal",
    )  # the ball inside a portal is still on its way

    def __init__(self, match):
        super().__init__(match)
        self.glide_from = self.feet(S.SERVE_POSITION)
        self.glide_t = self.glide_time = 0.0
        self.portals = None  # (entry point, exit spot) while open
        self.portal_t = 0.0  # time left before closed portals disappear
        self.zap_t = 0.0  # a cannon shot flying: its light shows for this long
        self.whine = None
        self.zap_to = (0.0, 0.0)

    # ---------------------------------------------------------------- robot movement
    def move_to(self, pos, duration):
        if pos != self.m.opp_pos:
            sfx.play("bot_move")
        self.glide_from = self.draw_pos()
        self.m.opp_pos = pos
        self.glide_t, self.glide_time = 0.0, duration

    def draw_pos(self):
        """Straight line at full speed, then stop dead with a little clunk."""
        to = self.feet(self.m.opp_pos)
        slide = self.glide_time * ROBOT_SLIDE
        k = min(self.glide_t / slide, 1.0) if slide > 0 else 1.0
        x, y = lerp_pt(self.glide_from, to, k)
        jolt = 1 if 0 < self.glide_t - slide < 0.06 else 0
        return (x, y + jolt)

    def muzzle(self):
        """Where his cannon is on screen (bottom-left of his sprite)."""
        x, y = self.draw_pos()
        return (x - 8, y - 9)

    # ---------------------------------------------------------------- tricks
    def reset(self):
        super().reset()
        self.portals = None

    def choose_trick(self):
        m = self.m
        if max(m.player_score, m.opp_score) < TRICKS_AFTER:
            return None
        options = [("portal", PORTAL_CHANCE), ("invisible", INVISIBLE_CHANCE)]
        if m.opp_pos in (
            1,
            2,
        ):  # the charge shot only fires straight down a bottom lane
            options.append(("charge", CHARGE_CHANCE))
        return self.pick(options)

    def windup(self, after_trick):
        if self.trick != "charge":
            return False
        m = self.m  # load the ball into the cannon and charge
        m.speed = m.level.fly_time / CHARGE_FLIGHT
        m.opp_anim.switch("charge")
        m.opp_anim.play("load")
        charge = m.level.windup_time + random.uniform(*CHARGE_TIME)
        self.whine = sfx.play(
            "bot_charge", last=charge
        )  # ends on its peak exactly as he fires
        m.set_phase("windup", charge)
        return True

    def hit(self):
        m = self.m
        if self.trick == "charge":  # fire the charged ball out of the cannon
            x, y = m.flight[0]
            m.opp_anim.play("fire")
            if self.whine is not None:
                self.whine.fadeout(60)
            sfx.play("bot_blast")
            fx.flash(CHARGE_FLASH, color=COL_GREEN)
            fx.shake(*CHARGE_SHAKE)
            fx.ripple(x, y, CHARGE_RIPPLE_TIME)
            m.trail, m.trail_colours = [], COL_CHARGE_TRAIL
            return True
        if self.trick == "invisible":  # zap the ball as he hits it: it vanishes
            m.opp_anim.play("aim")
            sfx.play("bot_zap")
            self.zap_t, self.zap_to = 0.12, m.flight[0]
            return True
        return False

    def flight(self, f):
        m = self.m
        if self.trick != "portal":
            return
        if not self.trick_done and f >= PORTAL_FIRE_AT:
            self._fire_portals()
        elif self.portals is not None and self.portal_t == 0 and f >= PORTAL_AT:
            m.set_phase("portal", PORTAL_GAP)  # into the portal...

    def _fire_portals(self):
        """His cannon shoots a portal into the ball's path on your half, and one opens at his end."""
        m = self.m
        self.trick_done = True
        start, end, arc = m.flight
        x, y = lerp_pt(start, end, PORTAL_AT)
        entry = (
            x,
            y - math.sin(math.pi * PORTAL_AT) * arc,
        )  # where the ball will be, in the air
        exit_spot = random.choice([p for p in range(4) if p != m.opp_pos])
        self.portals = (entry, exit_spot)
        m.opp_anim.play("aim")
        sfx.play("bot_portal")
        self.zap_t, self.zap_to = 0.12, entry

    def advance(self, phase):
        """...and out of the exit: it flies from there as if he'd hit it from that spot."""
        if phase != "portal":
            return False
        m = self.m
        if self.portals is not None:
            exit_spot = self.portals[1]
            m.target = S.LANDING_FOR[exit_spot]
            m.flight = (
                S.OPPONENT_HIT[exit_spot],
                S.PLAYER_BOUNCE[m.target],
                S.BALL_ARC,
            )
            m.set_phase("incoming", m.level.fly_time)
            self.portal_t = PORTAL_CLOSE
        return True

    def point_over(self, player_won):
        sfx.play(
            "bot_glitch" if player_won else "bot_beep"
        )  # glitches when you score, beeps when he does

    def match_over(self, player_won):
        if player_won:
            sfx.play("bot_shutdown")

    # ---------------------------------------------------------------- the ball
    def _charging(self):
        return (
            self.trick == "charge"
            and self.m.phase == "windup"
            and self.m.opp_anim.current != "load"
        )

    def ball_visible(self):
        return (
            self.m.phase != "portal" and not self._charging()
        )  # in a portal, or in his cannon

    def ball_hidden(self):
        return (
            self.trick == "invisible" and self.m.phase == "incoming"
        )  # only its shadow shows

    # ---------------------------------------------------------------- every frame
    def update(self, dt):
        self.glide_t += dt
        self.zap_t = max(0.0, self.zap_t - dt)
        if self.portal_t > 0:
            self.portal_t = max(0.0, self.portal_t - dt)
            if self.portal_t == 0:
                self.portals = None
        if self._charging():  # the floor trembles as he charges
            fx.shake(0.5 + self.m.t / self.m.duration, 0.05)

    def draw_effects(self, surf):
        m = self.m
        if self._charging():  # a green orb swelling at the cannon
            k = m.t / m.duration
            x, y = self.muzzle()
            r = 1 + round(k * 4) + (m.stage_time * 20 % 2 > 1)
            pygame.draw.circle(surf, COL_GREEN_DARK, (round(x), round(y)), r + 1)
            pygame.draw.circle(surf, COL_GREEN, (round(x), round(y)), r)
            surf.set_at((round(x), round(y)), "#BCBCBC")
        if self.zap_t > 0:  # the cannon shot on its way
            pygame.draw.line(surf, COL_GREEN, self.muzzle(), self.zap_to, 2)
        if self.portals is None:
            return
        entry, exit_spot = self.portals  # green swirling rings
        size = (
            self.portal_t / PORTAL_CLOSE if self.portal_t > 0 else 1.0
        )  # shrinking when closing
        for x, y in (entry, S.OPPONENT_HIT[exit_spot]):
            ring = pygame.Rect(0, 0, max(2, round(14 * size)), max(2, round(18 * size)))
            ring.center = (round(x), round(y))
            pygame.draw.ellipse(surf, "#000000", ring.inflate(2, 2))
            pygame.draw.ellipse(surf, COL_GREEN_DARK, ring)
            pygame.draw.ellipse(surf, COL_GREEN, ring, 2)
            for k in range(4):  # sparks spinning around the rim
                a = m.stage_time * 6 + k * math.pi / 2
                surf.set_at(
                    (
                        round(x + math.cos(a) * ring.w / 2),
                        round(y + math.sin(a) * ring.h / 2),
                    ),
                    "#BCBCBC",
                )
