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
        points_to_win=3,
        windup_time=0.25,
        fly_time=0.9,
        hit_window=0.45,
        return_time=0.7,
        opponent_miss_chance=0.2,
        sprite="esmeralda",
        portrait="esmeralda_portrait",
        background="gym2_bg",
        smash_chance=0.35,
        smash_after_points=0,
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
        opponent="Rival 2",
        points_to_win=5,
        windup_time=0.2,
        fly_time=0.75,
        hit_window=0.38,
        return_time=0.6,
        opponent_miss_chance=0.15,
        kit={"#004058": "#005800", "#E45C10": "#AC7C00", "#F83800": "#A81000"},
    ),
    Level(
        name="Final",
        opponent="The Boss",
        points_to_win=5,
        windup_time=0.15,
        fly_time=0.65,
        hit_window=0.32,
        return_time=0.55,
        opponent_miss_chance=0.1,
        kit={"#004058": "#881400", "#E45C10": "#E40058", "#F83800": "#D800CC"},
    ),
]
