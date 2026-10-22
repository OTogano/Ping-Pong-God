"""The levels: who you play, how fast, and on what stage.

Each opponent's tricks (and the numbers that tune them) live in their own file
in game/opponents/; `kind` says which one. A level with no kind plays straight.
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
    kind: str | None = None  # their tricks: game/opponents/<kind>.py (None = none)
    true_name: str | None = None  # shown instead of `opponent` once you've beaten them
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
    scoreboard_pos: tuple | None = (
        None  # where the scoreboard stands (None = settings.SCOREBOARD_POS)
    )
    props: tuple = ()  # animated people and things on the stage (see Prop)


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
        kind="greg",
        sprite="coach_greg",
        portrait="coach_greg_portrait",
        background="gym_floor",
    ),
    Level(
        name="Level 2",
        opponent="Esmeralda",
        points_to_win=3,
        windup_time=0.25,
        fly_time=0.9,
        hit_window=0.45,
        return_time=0.7,
        opponent_miss_chance=0.2,
        kind="esmeralda",
        sprite="esmeralda",
        portrait="esmeralda_portrait",
        background="gym2_bg",
        props=(
            Prop("gym_runner", 31, 16),  # on the second treadmill
            Prop("gym_stretch", 1, 139),  # yoga mat
            Prop("gym_sled", 236, 44, sweep_dy=140, period=9.0),
        ),
    ),  # up and down the turf
    Level(
        name="Level 3",
        opponent="Captain Squidy",
        points_to_win=5,
        windup_time=0.3,
        fly_time=0.8,
        hit_window=0.4,
        return_time=0.6,
        opponent_miss_chance=0.15,
        kind="squidy",
        sprite="squidy",
        portrait="squidy_portrait",
        background="ship_bg",
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
        kind="bot",
        sprite="bot",
        portrait="bot_portrait",
        background="lab_bg",
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
        opponent_miss_chance=0.25,
        kind="odin",
        sprite="pingpong_god",
        portrait="pingpong_god_portrait",
        background="throne_bg",
        scoreboard_pos=(34, 92),
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
