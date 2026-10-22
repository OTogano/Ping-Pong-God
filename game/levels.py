"""The four levels. Each one is a list of settings the match reads.

Opponent names, kits and backgrounds are placeholders until we design the
opponents; the numbers are a first pass at a difficulty curve to tune by play.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prop:
    """An animated sprite on the stage, e.g. someone running on a treadmill.
    assets/sprites/<sprite>.png + .json, looping its "idle" tag, drawn with its
    top-left at (x, y). sweep_dy/period make it move down and back up again."""

    sprite: str
    x: int
    y: int
    sweep_dy: int = 0
    period: float = 0.0


@dataclass(frozen=True)
class Level:
    name: str  # shown on the level card and at the start
    opponent: str  # opponent's name
    points_to_win: int
    windup_time: float  # opponent stands at a spot before hitting (the telegraph)
    fly_time: float  # ball travel from opponent to the bounce on your half
    hit_window: float  # time after the bounce in which you must press
    return_time: float  # your return travelling back to the opponent
    opponent_miss_chance: float  # chance the opponent misses each of your returns
    hints_until_score: int = (
        0  # key hints stay on until YOU have this many points (0 = off)
    )
    # Opponent colours until they get their own art: player colour -> opponent colour
    kit: dict[str, str] = field(default_factory=dict)
    background: str | None = None  # image in assets/backgrounds/ (None = plain floor)
    # Own art (assets/sprites/<sprite>.png + .json and <portrait>.png). None = the
    # player's sprite recoloured with `kit`.
    sprite: str | None = None
    portrait: str | None = None
    # A showy alternative to the normal swing on centre shots (it never changes
    # where the ball goes): the animation tag to play, and how often.
    special: str | None = None
    special_chance: float = 0.0
    # Smash: a much faster shot (it still lands where the telegraph says).
    # Uses the opponent's "windup_smash" (the tell) and "smash" animations.
    smash_chance: float = 0.0  # chance per hit once unlocked
    smash_after_points: int = (
        0  # only after this many points have been played (she "warms up")
    )
    smash_speed: float = 1.0  # 2.0 = the ball flies twice as fast
    smash_tell_extra: float = (
        0.0  # the tell lasts this much longer than a normal windup
    )
    # Animated people and things on the stage (see Prop below).
    props: tuple = ()
    # Opponents who fill the whole far end (Captain Squidy) stay at this point
    # (bottom-centre of their frame) instead of moving between OPPONENT_FEET, and are
    # drawn over the far end of the table. If they have "windup_d".."windup_k"
    # animations, the windup shows which paddle will hit.
    anchor: tuple | None = None
    # Juggle: he bats the ball between his paddles, then fires a fast shot from the
    # LAST paddle that touched it (so it's still readable if you track the ball).
    juggle_chance: float = 0.0
    juggle_hops: tuple = (3, 5)  # how many hops (min, max)
    juggle_hop_time: float = 0.2  # seconds per hop
    juggle_speed: float = 1.0  # speed of the shot that follows (1.6 = 60% faster)
    # Grab: a tentacle holds you during his windup. Press the right key once to
    # break free, then again (in the hit window) to return the ball.
    grab_chance: float = 0.0
    # Where the scoreboard stands on this stage (None = settings.SCOREBOARD_POS).
    scoreboard_pos: tuple | None = None
    # The Ping Pong God -------------------------------------------------------------
    true_name: str | None = None  # shown instead of `opponent` once you've beaten them
    feet: tuple | None = None  # their own four spots (None = settings.OPPONENT_FEET)
    over_table: bool = False  # drawn over the far end of the table (tall, floating)
    floats: bool = False  # glides between spots and bobs in the air
    power_hits: bool = False  # every hit: shockwave, shake and a glowing trail
    # Tricks, one at most per shot. Each unlocks once either score reaches *_after.
    redirect_chance: float = (
        0.0  # after the hit, his hand bends the ball to another lane
    )
    illusion_chance: float = (
        0.0  # fake balls fly with the real one (fakes cast no shadow)
    )
    illusion_after: int = 0
    illusion_count: tuple = (2, 3)
    rewind_chance: float = 0.0  # time runs back, he moves, and shoots again
    rewind_after: int = 0
    lightning: bool = False  # a storm: bolts in the sky and flashes now and then
    # BOT ----------------------------------------------------------------------------
    robotic: bool = False  # slides between spots in straight lines and stops dead
    tricks_after: int = 0  # his tricks unlock once either score reaches this
    portal_chance: float = (
        0.0  # the ball goes into a portal on your half and comes out of one at his end
    )
    invisible_chance: float = 0.0  # the ball turns invisible: only its shadow shows
    charge_chance: float = (
        0.0  # from a bottom spot: loads the ball in his cannon and fires it
    )


LEVELS = [
    Level(
        name="Tutorial",
        opponent="Coach Greg",
        points_to_win=3,
        windup_time=0.35,
        fly_time=1.1,
        hit_window=0.6,
        return_time=0.8,
        opponent_miss_chance=0.3,
        hints_until_score=1,
        sprite="coach_greg",
        portrait="coach_greg_portrait",
        background="gym_floor",
        special="belly",
        special_chance=0.2,
    ),  # belly bump on 1 in 5 centre shots,
    Level(
        name="Level 2",
        opponent="Esmeralda",
        points_to_win=5,
        windup_time=0.25,
        fly_time=0.9,
        hit_window=0.45,
        return_time=0.7,
        opponent_miss_chance=0.2,
        sprite="esmeralda",
        portrait="esmeralda_portrait",
        background="gym2_bg",
        smash_chance=0.35,
        smash_after_points=1,
        smash_speed=4.0,
        smash_tell_extra=0.2,
        props=(
            Prop("gym_runner", 31, 16),  # on the second treadmill
            Prop("gym_stretch", 1, 139),  # yoga mat
            Prop("gym_sled", 236, 44, sweep_dy=140, period=9.0),
        ),
    ),  # up and down the turf,
    Level(
        name="Level 3",
        opponent="Captain Squidy",
        points_to_win=5,
        windup_time=0.3,
        fly_time=0.8,
        hit_window=0.4,
        return_time=0.6,
        opponent_miss_chance=0.15,
        sprite="squidy",
        portrait="squidy_portrait",
        background="ship_bg",
        anchor=(128, 80),  # fills all four lanes
        juggle_chance=0.5,
        juggle_hops=(3, 5),
        juggle_hop_time=0.1,
        juggle_speed=3.0,
        grab_chance=0.25,
        scoreboard_pos=(30, 92),  # on the deck, clear of the rail and sea
        props=(
            Prop("ship_sea_l", 0, 0),  # waves rolling past the hull
            Prop("ship_sea_r", 233, 0),
            Prop("ship_cannon_l", 0, 48),  # pirates firing cannons
            Prop("ship_cannon_r", 192, 96),
        ),
    ),
    Level(
        name="Level 4",
        opponent="BOT",
        points_to_win=7,
        windup_time=0.25,
        fly_time=0.7,
        hit_window=0.35,
        return_time=0.6,
        opponent_miss_chance=0.2,
        sprite="bot",
        portrait="bot_portrait",
        background="lab_bg",
        robotic=True,
        tricks_after=1,  # all tricks once the first point is scored
        portal_chance=0.25,
        invisible_chance=0.25,
        charge_chance=0.3,
        props=(
            Prop("lab_flasks", 2, 50),  # bubbling on the bench
            Prop("lab_tesla", 228, 16),  # crackling
            Prop("lab_sci_flask", 16, 50),  # scientists running experiments...
            Prop("lab_sci_clipboard", 234, 96),  # ...and one writing down the match
            Prop("lab_sci_observer", 222, 180),
        ),
    ),
    Level(
        name="Final",
        opponent="♑□♎",
        true_name="Odin",
        points_to_win=10,
        windup_time=0.25,
        fly_time=0.6,
        hit_window=0.32,
        return_time=0.55,
        opponent_miss_chance=0.10,
        sprite="pingpong_god",
        portrait="pingpong_god_portrait",
        background="throne_bg",
        feet=((56, 86), (104, 62), (152, 62), (200, 86)),
        over_table=True,
        floats=True,
        power_hits=True,
        # escalation: redirect from the start, illusions from 2 points, rewind from 5
        redirect_chance=0.25,
        illusion_chance=0.25,
        illusion_after=2,
        illusion_count=(2, 3),
        rewind_chance=0.2,
        rewind_after=5,
        scoreboard_pos=(34, 92),
        lightning=True,
        props=(
            Prop("throne_runes", 0, 0),  # rune circles pulsing with light
            Prop("throne_brazier", 90, 4),
            Prop("throne_brazier", 154, 4),
            Prop("valkyrie_a", -4, 18),
            Prop("valkyrie_c", -4, 152),  # watching from the storm
            Prop("valkyrie_b", 220, 64),
            Prop("throne_snow", 0, 0),
        ),
    ),  # the blizzard, over everything on the stage
]
