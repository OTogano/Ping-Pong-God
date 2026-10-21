"""One match: the rally state machine, input and drawing.

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


def bezier(p0, p1, p2, p3, t):
    """Point t (0..1) along a cubic Bezier curve: starts at p0, ends at p3, pulled toward p1 and p2."""
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )


def curve(p0, p1, p2, t):
    """Point t (0..1) along a quadratic Bezier curve: from p0 to p2, pulled toward p1."""
    u = 1 - t
    return (
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
    )


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
        self.special = (
            False  # is the coming shot the opponent's showy special (e.g. belly bump)?
        )
        self.smash = False  # is the coming shot a smash (fast, flaming)?
        self.trail = []  # recent ball positions, for the smash's flame trail
        self.speed = 1.0  # the coming shot flies this many times faster (juggle shot)
        self.juggle_path = []  # paddles the ball still has to hop between (Captain Squidy)
        self.grab = False  # is a tentacle holding the player?
        self.grab_t = 0.0  # time since the grab started
        self.grab_out = (
            0.0  # time left for the tentacle to slither back after letting go
        )
        self.grab_lane = 0  # where the player was grabbed
        self.trick = None  # the Ping Pong God's trick for this shot: "redirect", "illusion", "rewind"
        self.trick_done = (
            False  # has the trick happened yet (redirect/rewind happen mid-flight)?
        )
        self.spike = False  # his answer after a rewind: a brutal fast shot
        self.bolt = []  # lightning bolt points while one is on screen
        self.bolt_t = 0.0
        self.illusions = []  # fake balls: [start, end, duration, time so far]
        self.pops = []  # where illusions vanished: [x, y, time left]
        self.bend = None  # a curved flight bends toward this point (redirect)
        self.arc_from = 0.0  # a flight that starts part-way through its hop (redirect)
        # Floating opponents glide from glide_from to their spot.
        self.glide_from = self._opp_feet(S.SERVE_POSITION)
        self.glide_t = self.glide_time = 0.0
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = (
            None  # after a miss, the right key stays lit so you learn the rule
        )
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
        self.bend = None
        self.arc_from = 0.0

    def _start_point(self):
        self._move_opponent(S.SERVE_POSITION, S.READY_TIME * 0.6)
        self.target = S.LANDING_FOR[self.opp_pos]
        self.ball = S.OPPONENT_HIT[self.opp_pos]
        self.ball_h = 0
        self.message = ""
        self.last_target = None
        self.special = False
        self.smash = False
        self.speed = 1.0
        self.juggle_path = []
        self.grab = False
        self.grab_out = 0.0
        self.trick = None
        self.spike = False
        self.illusions = []
        self.opp_anim.play("serve")  # e.g. Coach Greg blows his whistle
        self._set_phase("ready", S.READY_TIME)

    def _begin_windup(self, after_trick=False):
        """The opponent stands at their spot and winds up: this is the telegraph."""
        self.target = S.LANDING_FOR[self.opp_pos]
        lvl = self.level
        self.trick = None if after_trick else self._pick_trick()
        self.trick_done = False
        if not after_trick:
            self.speed = 1.0
            if random.random() < lvl.juggle_chance:
                self._start_juggle()
                return
        played = self.player_score + self.opp_score
        self.smash = (
            lvl.smash_chance > 0
            and played >= lvl.smash_after_points
            and random.random() < lvl.smash_chance
        )
        if self.smash:
            # The tell (Esmeralda: red eyes, grin, arms wide), held a bit longer to be fair.
            self.trail = []  # forget the last smash's flames (they were at the player's end)
            self.special = False
            self.opp_anim.switch("windup_smash")
            self._set_phase("windup", lvl.windup_time + lvl.smash_tell_extra)
            return
        self.special = (
            lvl.special is not None
            and self.target in (1, 2)
            and random.random() < lvl.special_chance
        )
        # A special has its own windup pose (Greg leans back before a belly bump).
        self.opp_anim.switch(self._windup_tag())
        duration = lvl.windup_time
        if not after_trick and random.random() < lvl.grab_chance:
            self._start_grab()
            duration += S.GRAB_TELL  # time to see the tentacle coming
        if self.spike:
            duration += S.SPIKE_TELL  # a beat longer before the spike
        self._set_phase("windup", duration)

    def _windup_tag(self):
        if self.special:
            return f"windup_{self.level.special}"
        # Opponents who never move (Captain Squidy) wind up the paddle that will hit.
        lane_tag = f"windup_{'dfjk'[self.opp_pos]}"
        return lane_tag if self.opp_anim.has(lane_tag) else "windup"

    def _opp_feet(self, pos):
        return (self.level.feet or S.OPPONENT_FEET)[pos]

    def _move_opponent(self, pos, duration):
        """Send the opponent to spot `pos` (floating ones glide there over `duration`)."""
        self.glide_from = self._opp_draw_pos()
        self.opp_pos = pos
        self.glide_t, self.glide_time = 0.0, duration

    def _opp_draw_pos(self):
        """Where to draw the opponent's feet right now (gliding and bobbing if they float)."""
        to = self._opp_feet(self.opp_pos)
        if not self.level.floats:
            return to
        k = min(self.glide_t / self.glide_time, 1.0) if self.glide_time > 0 else 1.0
        k = k * k * (3 - 2 * k)  # ease in and out
        x, y = lerp_pt(self.glide_from, to, k)
        return (x, y + (1 - math.cos(self.stage_time * 3)) * 1.5)  # hovering

    # ------------------------------------------------------------------ the Ping Pong God's tricks
    def _pick_trick(self):
        """At most one trick per shot; illusions and rewind unlock as the match goes on."""
        lvl = self.level
        lead = max(self.player_score, self.opp_score)
        options = [("redirect", lvl.redirect_chance)]
        if lead >= lvl.illusion_after:
            options.append(("illusion", lvl.illusion_chance))
        if lead >= lvl.rewind_after:
            options.append(("rewind", lvl.rewind_chance))
        r = random.random()
        for name, chance in options:
            if r < chance:
                return name
            r -= chance
        return None

    def _redirect(self):
        """His hand sweeps toward another lane and the ball bends there. Follow the hand!"""
        self.trick_done = True
        start, end, _ = self.flight
        f = self.t / self.duration
        new = random.choice([p for p in range(4) if p != self.target])
        self.target = new
        self.opp_anim.play(f"redirect_{'dfjk'[new]}")
        fx.flash(0.15, color=S.COL_DIVINE)
        here = self.ball
        ahead = lerp_pt(
            start, end, min(f + 0.3, 1.0)
        )  # it carries on the old way for a moment, then curves
        self._set_phase("incoming", self.duration - self.t + S.REDIRECT_EXTRA)
        self.flight = (here, S.PLAYER_BOUNCE[new], S.BALL_ARC)
        self.bend, self.arc_from = ahead, f

    def _rewind(self):
        """Time runs backwards: the ball flies back to him while he floats to a new spot,
        then he winds up again there (a fresh telegraph)."""
        self.trick_done = True
        self.illusions = []
        self.opp_anim.play("rewind")
        new = random.choice([p for p in range(4) if p != self.opp_pos])
        self._move_opponent(new, S.REWIND_TIME)
        self.flight = (self.ball, S.OPPONENT_HIT[new], S.BALL_ARC)
        fx.rewind(S.REWIND_TIME)
        self._set_phase("rewind", S.REWIND_TIME)

    def _spawn_illusions(self):
        """Fake balls to the other lanes, some faster and some slower than the real one."""
        lanes = [p for p in range(4) if p != self.target]
        random.shuffle(lanes)
        real = self.duration
        start = S.OPPONENT_HIT[self.opp_pos]
        self.illusions = [
            [
                start,
                S.PLAYER_BOUNCE[lane],
                real * random.uniform(*S.ILLUSION_SPEEDS),
                0.0,
            ]
            for lane in lanes[: random.randint(*self.level.illusion_count)]
        ]

    def _vanish_illusions(self):
        for start, end, dur, t in self.illusions:
            self.pops.append([*lerp_pt(start, end, min(t / dur, 1.0)), 0.2])
        self.illusions = []

    # ------------------------------------------------------------------ Captain Squidy's tricks
    def _start_juggle(self):
        """Bat the ball between paddles; the LAST paddle to touch it takes the shot."""
        lo, hi = self.level.juggle_hops
        path = [self.opp_pos]
        for _ in range(random.randint(lo, hi)):
            path.append(random.choice([p for p in range(4) if p != path[-1]]))
        self.juggle_path = path
        self._juggle_hop()

    def _juggle_hop(self):
        a, b = self.juggle_path[0], self.juggle_path[1]
        self.opp_anim.play(f"bat_{'dfjk'[a]}")
        self.flight = (S.OPPONENT_HIT[a], S.OPPONENT_HIT[b], S.JUGGLE_ARC)
        self._set_phase("juggle", self.level.juggle_hop_time)

    def _start_grab(self):
        self.grab = True
        self.grab_t = 0.0
        self.grab_lane = self.player_pos
        self.message = "Grabbed!"

    def _release_grab(self):
        if self.grab:
            self.grab = False
            self.grab_out = S.GRAB_RETRACT
            if self.message == "Grabbed!":
                self.message = ""

    def _opponent_hits(self):
        self.target = S.LANDING_FOR[self.opp_pos]
        self.flight = (
            S.OPPONENT_HIT[self.opp_pos],
            S.PLAYER_BOUNCE[self.target],
            S.BALL_ARC,
        )
        if self.smash:
            self.opp_anim.play("smash")
            self.trail = []
            hit = S.OPPONENT_HIT[self.opp_pos]
            fx.flash(S.SMASH_FLASH, color=S.SMASH_FLASH_COLOR)
            fx.shake(*S.SMASH_SHAKE)
            fx.ripple(hit[0], hit[1], S.SMASH_RIPPLE_TIME)
            self._set_phase("incoming", self.level.fly_time / self.level.smash_speed)
            return
        if self.level.power_hits:  # the Ping Pong God: every hit lands like thunder
            hit = S.OPPONENT_HIT[self.opp_pos]
            self.trail = []
            if self.spike:  # ...and the spike after a rewind even more so
                fx.flash(S.SPIKE_FLASH, color=S.COL_LIGHTNING)
                fx.shake(*S.SPIKE_SHAKE)
                fx.ripple(hit[0], hit[1], S.SPIKE_RIPPLE_TIME)
            else:
                fx.shake(*S.POWER_SHAKE)
                fx.ripple(hit[0], hit[1], S.POWER_RIPPLE_TIME)
        if self.special and self.level.special:
            self.opp_anim.play(self.level.special)
        elif self.trick == "illusion":
            self.opp_anim.play("illusion")
        else:
            self.opp_anim.play(f"swing_{'dfjk'[self.opp_pos]}")
        self._set_phase("incoming", self.level.fly_time / self.speed)
        if self.trick == "illusion":
            self._spawn_illusions()

    def _player_returns(self):
        self.smash = False
        self.spike = False
        self.speed = 1.0
        self._vanish_illusions()
        # The opponent moves to their next spot as the ball travels:
        # that movement IS the telegraph for the next shot.
        self._move_opponent(
            random.randrange(4), self.level.return_time * S.GLIDE_FRACTION
        )
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self._set_phase("return", self.level.return_time)

    def _point(self, player_won, message):
        self._release_grab()
        self._vanish_illusions()
        if player_won:
            self.player_score += 1
        else:
            self.opp_score += 1
            self.last_target = self.target
            fx.shake(*S.MISS_SHAKE)
        self.scoreboard.set(self.opp_score, self.player_score)
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
            if player_won and self.level.true_name:  # the hood comes down
                self.message += f"\n{self.level.opponent} was {self.level.true_name}!"
            if player_won and self.app:
                self.unlocked = self.app.progress.mark_won(self.level_index)
            self._set_phase("over", S.RESULT_DELAY)
        else:
            self._set_phase("point", S.POINT_PAUSE)

    def _advance(self):
        if self.phase == "ready":
            self.message = ""  # clears the level name after the first serve
            self._begin_windup()
        elif self.phase == "windup":
            self._opponent_hits()
        elif self.phase == "rewind":  # shoots again from his new spot: a spike
            self.spike = True
            self.speed = S.SPIKE_SPEED
            self._begin_windup(after_trick=True)
        elif self.phase == "juggle":
            self.juggle_path.pop(0)
            if len(self.juggle_path) > 1:
                self._juggle_hop()
            else:  # last paddle: wind it up, then a fast shot
                self.opp_pos = self.juggle_path.pop()
                self.speed = self.level.juggle_speed
                self._begin_windup(after_trick=True)
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
                self._begin_windup()
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
                score=f"You {self.player_score} - {self.opp_score} "
                f"{self.level.true_name if self.won and self.level.true_name else self.level.opponent}",
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
        if self.grab and self.phase in ("windup", "incoming", "window"):
            # Held by a tentacle: the right key breaks free (this press never counts as
            # early), then you need a second press to hit. A wrong key loses the point.
            self.keys.press(pressed)
            if pressed == self.target:
                self._release_grab()
                fx.shake(1, 0.1)
            else:
                self._point(False, "Wrong side!")
            return
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
        if self.grab:
            self.grab_t += dt
        self.grab_out = max(0.0, self.grab_out - dt)
        self.glide_t += dt
        self._update_storm(dt)
        for ill in self.illusions:
            ill[3] += dt
        for ill in [
            i for i in self.illusions if i[3] >= i[2]
        ]:  # an illusion reaches the table: it vanishes
            self.illusions.remove(ill)
            self.pops.append([*ill[1], 0.2])
        for pop in self.pops:
            pop[2] -= dt
        self.pops = [p for p in self.pops if p[2] > 0]
        self.t += dt

        if self.phase in ("incoming", "window", "return", "juggle", "rewind"):
            start, end, arc = self.flight
            f = min(self.t / self.duration, 1.0)
            self.ball = (
                curve(start, self.bend, end, f) if self.bend else lerp_pt(start, end, f)
            )
            hop = (
                self.arc_from + (1 - self.arc_from) * f
            )  # a bent flight continues its hop
            self.ball_h = math.sin(math.pi * hop) * arc  # simple hop: up then down
            if self.phase == "incoming" and self.trick and not self.trick_done:
                if self.trick == "redirect" and f >= S.REDIRECT_AT:
                    self._redirect()
                elif self.trick == "rewind" and f >= S.REWIND_AT:
                    self._rewind()
            if self.smash or (
                self.level.power_hits and self.phase in ("incoming", "window")
            ):
                self.trail = (
                    self.trail + [(self.ball[0], self.ball[1] - self.ball_h)]
                )[-S.FLAME_TRAIL :]
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
        self._draw_bolt(surf)  # lightning in the sky, behind everything on the stage
        for prop, anim in self.props:
            dy = 0
            if (
                prop.sweep_dy and prop.period
            ):  # start low, push up the lane, walk back down
                phase = (self.stage_time % prop.period) / prop.period
                dy = round(prop.sweep_dy * abs(2 * phase - 1))
            surf.blit(anim.image, (prop.x, prop.y + dy))
        # The opponent stands behind the table, so draw them first: their feet
        # tuck behind its far edge.
        opp = self.opp_anim.image
        feet = self._opp_draw_pos()
        feet = (round(feet[0]), round(feet[1]))
        if self.level.anchor is None and not self.level.over_table:
            surf.blit(opp, opp.get_rect(midbottom=feet))
        surf.blit(self.table, S.TABLE_SPRITE_POS)
        self._draw_ball_shadow(surf)
        surf.blit(self.net, S.NET_SPRITE_POS)
        if self.level.anchor is not None:  # fills the far end, leaning over the table
            surf.blit(opp, opp.get_rect(midbottom=self.level.anchor))
        elif self.level.over_table:  # floats above the far end of the table
            surf.blit(opp, opp.get_rect(midbottom=feet))
        self.scoreboard.draw(surf)
        # After a miss, the correct key stays lit so the rule is learnable.
        self.keys.draw(surf, lit=self._hint_key())
        me = self.player_anim.image
        feet = S.PLAYER_FEET[self.player_pos]
        if (
            self.grab and self.grab_t > S.GRAB_REACH
        ):  # struggling in the tentacle's grip
            feet = (feet[0] + random.choice((-1, 0, 1)), feet[1])
        surf.blit(me, me.get_rect(midbottom=feet))
        self._draw_grab(surf)
        self._draw_flames(surf)
        self._draw_illusions(surf)
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

    def _draw_flames(self, surf):
        """The smash's fire trail: blobs along the ball's recent path, hot near the ball."""
        # Only while the ball is actually flying or bouncing, never during the windup.
        if not (
            (self.smash or self.level.power_hits)
            and self.phase in ("incoming", "window")
        ):
            return
        colours = S.COL_FLAMES if self.smash else S.COL_POWER_TRAIL
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            age = n - 1 - i  # 0 = newest
            colour = colours[min(age * len(colours) // max(n, 1), len(colours) - 1)]
            radius = max(1, 4 - age // 3)
            jitter = random.randint(-1, 1)  # flicker
            pygame.draw.circle(
                surf, colour, (round(x) + jitter, round(y) - age // 2), radius
            )

    def _draw_grab(self, surf):
        """Captain Squidy's grabbing tentacle: a tapering Bezier curve from his body to you."""
        if self.grab:
            reach = min(self.grab_t / S.GRAB_REACH, 1.0)  # stretching out
        elif self.grab_out > 0:
            reach = self.grab_out / S.GRAB_RETRACT  # slithering back
        else:
            return
        side = -1 if self.grab_lane < 2 else 1  # down the side of the table nearest you
        fx_, fy = S.PLAYER_FEET[self.grab_lane]
        waist = (fx_, fy - 16)
        wob = math.sin(self.stage_time * 7) * 3  # it writhes
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
            pygame.draw.circle(surf, S.COL_TENTACLE, (round(x), round(y)), round(r))
        for (x, y), r in zip(pts, radius):  # a light streak along the top
            pygame.draw.circle(
                surf,
                S.COL_TENTACLE_LIGHT,
                (round(x - r / 2), round(y - r / 2)),
                max(1, round(r / 3)),
            )
        for (x, y), r in list(zip(pts, radius))[3::5]:  # suckers on the underside
            surf.set_at((round(x + r / 2), round(y + r / 2)), S.COL_SUCKER)
        if reach >= 1 and self.grab:  # coiled around the player's waist
            for dy in (-4, 3):
                band = pygame.Rect(0, 0, 26, 7)
                band.center = (waist[0], waist[1] + dy)
                pygame.draw.ellipse(surf, "#000000", band.inflate(2, 2))
                pygame.draw.ellipse(surf, S.COL_TENTACLE, band)
                pygame.draw.line(
                    surf,
                    S.COL_TENTACLE_LIGHT,
                    (band.left + 4, band.top + 1),
                    (band.right - 6, band.top + 1),
                )
                for sx in range(band.left + 4, band.right - 2, 5):
                    surf.set_at((sx, band.bottom - 2), S.COL_SUCKER)

    def _update_storm(self, dt):
        """Now and then lightning strikes in the sky beside the island."""
        self.bolt_t = max(0.0, self.bolt_t - dt)
        if (
            not self.level.lightning
            or self.bolt_t > 0
            or random.random() >= S.LIGHTNING_CHANCE * dt
        ):
            return
        x = random.choice(
            (random.randint(6, 24), random.randint(232, 250))
        )  # left or right of the island
        y, self.bolt = 0, [(x, 0)]
        while y < random.randint(80, 200):  # zig-zag down
            y += random.randint(6, 14)
            x = min(max(x + random.randint(-5, 5), 2), S.WIDTH - 3)
            self.bolt.append((x, y))
        self.bolt_t = S.LIGHTNING_TIME
        if self.phase not in (
            "incoming",
            "window",
        ):  # never blind you while the ball is coming
            fx.flash(S.LIGHTNING_FLASH, 0.1, color=S.COL_LIGHTNING)

    def _draw_bolt(self, surf):
        if self.bolt_t > 0 and len(self.bolt) > 1:
            pygame.draw.lines(surf, S.COL_LIGHTNING_GLOW, False, self.bolt, 3)
            pygame.draw.lines(surf, S.COL_LIGHTNING, False, self.bolt, 1)

    def _draw_illusions(self, surf):
        """Fake balls look exactly like the real one, except they cast no shadow."""
        for start, end, dur, t in self.illusions:
            f = min(t / dur, 1.0)
            x, y = lerp_pt(start, end, f)
            h = math.sin(math.pi * f) * S.BALL_ARC
            surf.blit(
                self.ball_img, self.ball_img.get_rect(center=(round(x), round(y - h)))
            )
        for x, y, left in self.pops:  # vanishing: a burst of sparkles
            r = round((0.2 - left) * 30) + 1
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                surf.set_at((round(x) + dx, round(y) + dy), S.COL_DIVINE)

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
