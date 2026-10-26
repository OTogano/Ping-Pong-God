"""One match: the rally state machine, input and drawing.

The rally is a loop of phases:

    ready -> windup -> incoming -> window -> return -> windup -> ...
                                     |                   |
                                     +-> point (miss)    +-> point (opponent misses)

Each phase has a duration; `self.t` counts up through it. When it reaches the
duration, `_advance()` moves to the next phase.

Opponents add their own tricks (and sometimes their own phases, like Squidy's
"juggle") through the hooks in game/opponents/base.py, so this file only has
what every match shares.
"""

import math
import random

import pygame

from game import controls
from game import settings as S
from game.audio import sfx
from game.gfx.effects import fx
from game.gfx.geometry import curve, lerp_pt
from game.gfx.sprites import Animator, load_animations, load_image, load_strip, recolour
from game.gfx.text import BitmapFont
from game.gfx.ui import KeyIcons, Scoreboard
from game.levels import LEVELS
from game.opponents import make_opponent
from game.scenes.base import Scene
from game.scenes.level_select import LevelSelectScene
from game.scenes.pause import PauseScene
from game.scenes.result import ResultScene


class Match(Scene):
    def __init__(self, level_index=0):
        self.level_index = level_index
        self.level = LEVELS[level_index]
        self.font = BitmapFont()
        # The level's stage, drawn under everything (plain floor colour if it has none).
        self.background = (
            load_image("backgrounds", f"{self.level.background}.png")
            if self.level.background
            else None
        )
        # Animated stage props (people working out, ...), each looping its "idle" tag.
        self.props = [
            (prop, Animator(load_animations(prop.sprite))) for prop in self.level.props
        ]
        self.stage_time = 0.0
        self.table = load_image("sprites", "table.png")
        self.net = load_image("sprites", "net.png")
        self.ball_img, self.ball_squash, self.ball_shadow = load_strip(
            "sprites/ball.png", S.BALL_SIZE
        )
        self.scoreboard = Scoreboard(self.level.scoreboard_pos)
        self.keys = KeyIcons()
        self.squash = 0.0
        anims = load_animations("player")
        self.player_anim = Animator(anims)
        # Opponents with their own art load it; the rest wear the player's sprite in their kit.
        opp_anims = (
            load_animations(self.level.sprite)
            if self.level.sprite
            else recolour(anims, self.level.kit)
        )
        self.opp_anim = Animator(opp_anims)
        self.speed = 1.0  # the coming shot flies this many times faster (smash, juggle shot, ...)
        self.trail = []  # recent ball positions, for a glowing/flaming trail
        self.trail_colours = (
            None  # the trail's colours (newest first), or None for no trail
        )
        self.bend = None  # a curved flight bends toward this point (Odin's redirect)
        self.arc_from = 0.0  # a flight that starts part-way through its hop
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = (
            None  # after a miss, the right key stays lit so you learn the rule
        )
        # Rally state; _start_point() and set_phase() fill these in.
        self.phase, self.duration, self.t = "ready", 0.0, 0.0
        self.flight = ((0.0, 0.0), (0.0, 0.0), 0.0)  # (start, end, arc height)
        self.won = self.unlocked = False  # set when the match ends
        self.bounced = False
        self.opponent = make_opponent(self)  # their tricks: game/opponents/<kind>.py
        self._start_point()
        # First serve: show the level name and wait a little longer.
        self.message = f"{self.level.name}\nvs {self.level.opponent}"
        self.duration = S.INTRO_TIME

    # ------------------------------------------------------------------ phases
    def set_phase(self, name, duration):
        self.phase = name
        self.duration = duration
        self.t = 0.0
        self.bend = None
        self.arc_from = 0.0

    def _start_point(self):
        self.opponent.move_to(S.SERVE_POSITION, S.READY_TIME * 0.6)
        self.target = S.LANDING_FOR[self.opp_pos]
        self.ball = S.OPPONENT_HIT[self.opp_pos]
        self.ball_h = 0
        self.message = ""
        self.last_target = None
        self.speed = 1.0
        self.trail_colours = None
        self.opponent.reset()
        self.opp_anim.play("serve")  # e.g. Coach Greg blows his whistle
        if self.opponent.serve_sound:
            sfx.play(self.opponent.serve_sound)
        self.set_phase("ready", S.READY_TIME)

    def begin_windup(self, after_trick=False):
        """The opponent stands at their spot and winds up: this is the telegraph.
        after_trick: this windup follows a trick (juggle, rewind), so no new trick now."""
        self.target = S.LANDING_FOR[self.opp_pos]
        opp = self.opponent
        opp.trick = None if after_trick else opp.choose_trick()
        opp.trick_done = False
        if not after_trick:
            self.speed = 1.0
        if opp.windup(after_trick):  # the opponent set up a windup of their own
            return
        self.opp_anim.switch(opp.windup_tag())
        self.set_phase("windup", self.level.windup_time + opp.windup_extra())

    def _opponent_hits(self):
        self.target = S.LANDING_FOR[self.opp_pos]
        self.flight = (
            S.OPPONENT_HIT[self.opp_pos],
            S.PLAYER_BOUNCE[self.target],
            S.BALL_ARC,
        )
        self.trail_colours = None
        sfx.play("hit")
        if (
            not self.opponent.hit()
        ):  # True: they played their own animation (smash, ...)
            self.opp_anim.play(f"swing_{'dfjk'[self.opp_pos]}")
        self.set_phase("incoming", self.level.fly_time / self.speed)
        self.opponent.after_hit()

    def _player_returns(self):
        self.speed = 1.0
        self.trail_colours = None
        self.opponent.returned()
        # The opponent moves to their next spot as the ball travels:
        # that movement IS the telegraph for the next shot.
        self.opponent.move_to(
            random.randrange(4), self.level.return_time * S.GLIDE_FRACTION
        )
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self.set_phase("return", self.level.return_time)
        self.bounced = False  # your return bounces once on their half

    def point(self, player_won, message):
        self.opponent.point_over(player_won)
        if player_won:
            self.player_score += 1
        else:
            self.opp_score += 1
            self.last_target = self.target
            fx.shake(*S.MISS_SHAKE)
        self.scoreboard.set(self.opp_score, self.player_score)
        sfx.play("flip")
        self.message = message
        self.opp_anim.after("point_lost" if player_won else "point_won")
        self.player_anim.after(
            "point_won" if player_won else "point_lost"
        )  # after his swing finishes
        if self.level.points_to_win in (self.player_score, self.opp_score):
            self.won = player_won
            self.opp_anim.after("match_lost" if player_won else "match_won", loop=True)
            self.player_anim.after(
                "match_won" if player_won else "match_lost", loop=True
            )
            self.message = f"{message}\n{'You win!' if player_won else 'You lose!'}"
            if player_won and self.level.true_name:  # e.g. the hood comes down
                self.message += f"\n{self.level.opponent} was {self.level.true_name}!"
            sfx.play("match_won" if player_won else "match_lost")
            self.opponent.match_over(player_won)
            if player_won and self.app:
                self.unlocked = self.app.progress.mark_won(self.level_index)
            self.set_phase("over", S.RESULT_DELAY)
        else:
            # The point's sound (on the last point of a match, the jingle plays instead).
            if player_won:
                sfx.play("point_won")
            else:
                sfx.play(
                    "wrong" if message == "Wrong side!" else "point_lost",
                    fallback="point_lost",
                )
            self.set_phase("point", S.POINT_PAUSE)

    def _advance(self):
        if self.opponent.advance(
            self.phase
        ):  # a phase of the opponent's own (juggle, portal, rewind)
            return
        if self.phase == "ready":
            self.message = ""  # clears the level name after the first serve
            self.begin_windup()
        elif self.phase == "windup":
            self._opponent_hits()
        elif self.phase == "incoming":
            self.flight = (
                S.PLAYER_BOUNCE[self.target],
                S.PLAYER_HIT[self.target],
                S.WINDOW_ARC,
            )
            self.squash = S.BALL_SQUASH_TIME  # the ball just bounced on your side
            sfx.play("bounce")
            self.set_phase("window", self.level.hit_window)
        elif self.phase == "window":
            self.point(False, "Too late!")
        elif self.phase == "return":
            if random.random() < self.level.opponent_miss_chance:
                self.point(True, "Opponent missed!")
            else:
                self.begin_windup()
        elif self.phase == "point":
            self._start_point()
        elif self.phase == "over":
            self._show_result()

    def _show_result(self):
        self.set_phase("done", math.inf)
        if not self.app:
            return
        last = self.level_index == len(LEVELS) - 1
        name = (
            self.level.true_name
            if self.won and self.level.true_name
            else self.level.opponent
        )
        self.app.push(
            ResultScene(
                won=self.won,
                score=f"You {self.player_score} - {self.opp_score} {name}",
                retry=self.restart,
                level_select=self.level_select,
                next_level=None if last else self.next_level,
                unlocked=LEVELS[self.level_index + 1].name if self.unlocked else None,
                champion=self.won and last,
            )
        )

    # ------------------------------------------------------------------ input
    def restart(self):
        sfx.stop_all()
        if self.app:
            self.app.switch(Match(self.level_index))

    def next_level(self):
        sfx.stop_all()
        if self.app:
            self.app.switch(Match(self.level_index + 1))

    def level_select(self):
        sfx.stop_all()
        if self.app:
            self.app.switch(LevelSelectScene(self.level_index))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if controls.pressed(event, controls.BACK) and self.app:
            sfx.pause()
            sfx.play("pause")
            self.app.push(
                PauseScene(
                    self.restart, self.level_select, self.app.renderer.supports_crt
                )
            )
            return
        if event.key not in S.HIT_KEYS:
            return

        pressed = S.HIT_KEYS.index(event.key)
        if self.opponent.press(pressed):  # e.g. breaking free of Squidy's tentacle
            return
        # The player sprite always jumps to the pressed spot and swings,
        # even on a miss, so the controls feel responsive.
        self.player_pos = pressed
        self.keys.press(pressed)
        self.player_anim.play(f"swing_{'dfjk'[pressed]}")

        if self.phase in self.opponent.early_phases and S.EARLY_PRESS_IS_MISS:
            self.point(False, "Too early!")
        elif self.phase == "window":
            if pressed == self.target:
                fx.flash(S.RETURN_FLASH)
                sfx.play("return", fallback="hit")
                self._player_returns()
            else:
                self.point(False, "Wrong side!")

    # ------------------------------------------------------------------ update
    def update(self, dt):
        # Crouch in the "ready" pose while the ball is yours to hit.
        if self.phase not in ("over", "done"):
            self.player_anim.loop(
                "ready" if self.phase in ("incoming", "window") else "idle"
            )
        self.player_anim.update(dt)
        if self.phase not in ("windup", "over", "done"):
            self.opp_anim.loop("idle")
            # Now and then, while waiting, the opponent fidgets (Greg mops his head, Esmeralda flips her hair).
            if (
                self.phase in ("ready", "point")
                and not self.opp_anim.busy
                and random.random() < S.FIDGET_CHANCE * dt
            ):
                self.opp_anim.play("fidget")
        self.opp_anim.update(dt)
        self.scoreboard.update(dt)
        self.keys.update(dt)
        self.stage_time += dt
        for _, anim in self.props:
            anim.update(dt)
        self.squash = max(0.0, self.squash - dt)
        self.opponent.update(dt)
        self.t += dt

        if self.phase in ("incoming", "window", "return") + self.opponent.flight_phases:
            start, end, arc = self.flight
            f = min(self.t / self.duration, 1.0)
            self.ball = (
                curve(start, self.bend, end, f) if self.bend else lerp_pt(start, end, f)
            )
            hop = (
                self.arc_from + (1 - self.arc_from) * f
            )  # a bent flight continues its hop
            self.ball_h = math.sin(math.pi * hop) * arc  # simple hop: up then down
            if self.phase == "incoming":
                self.opponent.flight(f)  # mid-flight tricks
            elif (
                self.phase == "return" and f >= S.RETURN_BOUNCE_AT and not self.bounced
            ):
                self.bounced = True  # your return lands on their half
                sfx.play("bounce", volume=S.FAR_BOUNCE_VOLUME)
            if self.trail_colours and self.phase in ("incoming", "window"):
                self.trail = (
                    self.trail + [(self.ball[0], self.ball[1] - self.ball_h)]
                )[-S.TRAIL_LENGTH :]
        elif self.phase in ("ready", "windup"):
            self.ball = S.OPPONENT_HIT[self.opp_pos]
            self.ball_h = 0

        if self.t >= self.duration:
            self._advance()

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        if self.background:
            surf.blit(self.background, (0, 0))
        else:
            surf.fill(S.COL_FLOOR)
        self.opponent.draw_stage(surf)  # e.g. lightning in the sky, behind the props
        for prop, anim in self.props:
            dy = 0
            if (
                prop.sweep_dy and prop.period
            ):  # start low, push up the lane, walk back down
                phase = (self.stage_time % prop.period) / prop.period
                dy = round(prop.sweep_dy * abs(2 * phase - 1))
            surf.blit(anim.image, (prop.x, prop.y + dy))
        # Most opponents stand behind the table, so they're drawn first: their feet
        # tuck behind its far edge. Big or floating ones are drawn over its far end.
        opp = self.opp_anim.image
        x, y = self.opponent.draw_pos()
        opp_rect = opp.get_rect(midbottom=(round(x), round(y)))
        if self.opponent.behind_table:
            surf.blit(opp, opp_rect)
        surf.blit(self.table, S.TABLE_SPRITE_POS)
        self._draw_ball_shadow(surf)
        surf.blit(self.net, S.NET_SPRITE_POS)
        if not self.opponent.behind_table:
            surf.blit(opp, opp_rect)
        self.scoreboard.draw(surf)
        # After a miss, the correct key stays lit so the rule is learnable.
        self.keys.draw(surf, lit=self._hint_key())
        me = self.player_anim.image
        fx_, fy = S.PLAYER_FEET[self.player_pos]
        surf.blit(me, me.get_rect(midbottom=(fx_ + self.opponent.player_offset(), fy)))
        self.opponent.draw_effects(surf)  # tentacles, portals, illusions...
        self._draw_trail(surf)
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

    def _draw_trail(self, surf):
        """A smash's flames or a power shot's glow: blobs along the ball's recent path."""
        # Only while the ball is actually flying or bouncing, never during the windup.
        colours = self.trail_colours
        if not colours or self.phase not in ("incoming", "window"):
            return
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            age = n - 1 - i  # 0 = newest
            colour = colours[min(age * len(colours) // max(n, 1), len(colours) - 1)]
            radius = max(1, 4 - age // 3)
            jitter = random.randint(-1, 1)  # flicker
            pygame.draw.circle(
                surf, colour, (round(x) + jitter, round(y) - age // 2), radius
            )

    def _ball_visible(self):
        return (
            self.phase not in ("point", "over", "done") and self.opponent.ball_visible()
        )

    def _draw_ball_shadow(self, surf):
        if self._ball_visible():
            bx, by = self.ball
            surf.blit(
                self.ball_shadow,
                self.ball_shadow.get_rect(center=(round(bx), round(by))),
            )

    def _draw_ball(self, surf):
        if not self._ball_visible() or self.opponent.ball_hidden():
            return
        bx, by = self.ball
        image = self.ball_squash if self.squash > 0 else self.ball_img
        surf.blit(image, image.get_rect(center=(round(bx), round(by - self.ball_h))))
