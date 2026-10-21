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
        self.player_score = 0
        self.opp_score = 0
        self.player_pos = 1  # player rests at bottom left
        self.opp_pos = S.SERVE_POSITION
        self.message = ""
        self.last_target = None  # shown briefly after a miss so you learn the rule
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

    def _start_point(self):
        self.opp_pos = S.SERVE_POSITION
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
        self.opp_anim.play("serve")  # e.g. Coach Greg blows his whistle
        self._set_phase("ready", S.READY_TIME)

    def _begin_windup(self, after_juggle=False):
        """The opponent stands at their spot and winds up: this is the telegraph."""
        self.target = S.LANDING_FOR[self.opp_pos]
        lvl = self.level
        if not after_juggle:
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
        if not after_juggle and random.random() < lvl.grab_chance:
            self._start_grab()
            duration += S.GRAB_TELL  # time to see the tentacle coming
        self._set_phase("windup", duration)

    def _windup_tag(self):
        if self.special:
            return f"windup_{self.level.special}"
        # Opponents who never move (Captain Squidy) wind up the paddle that will hit.
        lane_tag = f"windup_{'dfjk'[self.opp_pos]}"
        return lane_tag if self.opp_anim.has(lane_tag) else "windup"

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
        if self.special and self.level.special:
            self.opp_anim.play(self.level.special)
        else:
            self.opp_anim.play(f"swing_{'dfjk'[self.opp_pos]}")
        self._set_phase("incoming", self.level.fly_time / self.speed)

    def _player_returns(self):
        # The opponent moves to their next spot as the ball travels:
        # that movement IS the telegraph for the next shot.
        self.smash = False
        self.speed = 1.0
        self.opp_pos = random.randrange(4)
        self.flight = (self.ball, S.OPPONENT_HIT[self.opp_pos], S.BALL_ARC)
        self._set_phase("return", self.level.return_time)

    def _point(self, player_won, message):
        self._release_grab()
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
            self.opp_anim.switch("match_lost" if player_won else "match_won")
            self.message = f"{message}\n{'You win!' if player_won else 'You lose!'}"
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
        elif self.phase == "juggle":
            self.juggle_path.pop(0)
            if len(self.juggle_path) > 1:
                self._juggle_hop()
            else:  # last paddle: wind it up, then a fast shot
                self.opp_pos = self.juggle_path.pop()
                self.speed = self.level.juggle_speed
                self._begin_windup(after_juggle=True)
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
                score=f"You {self.player_score} - {self.opp_score} {self.level.opponent}",
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
            # Now and then, while waiting, the opponent wipes their brow (if they have a "mop").
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
        self.t += dt

        if self.phase in ("incoming", "window", "return", "juggle"):
            start, end, arc = self.flight
            f = min(self.t / self.duration, 1.0)
            self.ball = lerp_pt(start, end, f)
            self.ball_h = math.sin(math.pi * f) * arc  # simple hop: up then down
            if self.smash:
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
            for prop, anim in self.props:
                dy = 0
                if (
                    prop.sweep_dy and prop.period
                ):  # start low, push up the lane, walk back down
                    phase = (self.stage_time % prop.period) / prop.period
                    dy = round(prop.sweep_dy * abs(2 * phase - 1))
                surf.blit(anim.image, (prop.x, prop.y + dy))
        else:
            surf.fill(S.COL_FLOOR)
        # The opponent stands behind the table, so draw them first: their feet
        # tuck behind its far edge.
        opp = self.opp_anim.image
        if self.level.anchor is None:
            surf.blit(opp, opp.get_rect(midbottom=S.OPPONENT_FEET[self.opp_pos]))
        surf.blit(self.table, S.TABLE_SPRITE_POS)
        self._draw_ball_shadow(surf)
        surf.blit(self.net, S.NET_SPRITE_POS)
        if self.level.anchor is not None:  # fills the far end, leaning over the table
            surf.blit(opp, opp.get_rect(midbottom=self.level.anchor))
        self.scoreboard.draw(surf)
        # After a miss, the correct key stays lit so the rule is learnable.
        self.keys.draw(surf, lit=self._hint_key())
        # Opponent first so the ball and player draw over them.
        me = self.player_anim.image
        feet = S.PLAYER_FEET[self.player_pos]
        if (
            self.grab and self.grab_t > S.GRAB_REACH
        ):  # struggling in the tentacle's grip
            feet = (feet[0] + random.choice((-1, 0, 1)), feet[1])
        surf.blit(me, me.get_rect(midbottom=feet))
        self._draw_grab(surf)
        surf.blit(me, me.get_rect(midbottom=S.PLAYER_FEET[self.player_pos]))
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
        if not (self.smash and self.phase in ("incoming", "window")):
            return
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            age = n - 1 - i  # 0 = newest
            colour = S.COL_FLAMES[
                min(age * len(S.COL_FLAMES) // max(n, 1), len(S.COL_FLAMES) - 1)
            ]
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
