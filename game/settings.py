"""Game-wide settings: screen, palette, controls, timings and table layout.

Everything you'll want to tune lives here, so gameplay tweaks never mean
digging through the match code.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------
TITLE = "Ping Pong God"
WIDTH, HEIGHT = 256, 224  # internal "pixel" resolution (SNES-sized canvas)
SCALE = 3  # window = 768 x 672; keep it a whole number
FPS = 60
FORCE_SOFTWARE_RENDERER = False

# ---------------------------------------------------------------------------
# Palette (NES, as provided). Index order matches the list you pasted.
# ---------------------------------------------------------------------------
NES_PALETTE = [
    "#7C7C7C",
    "#0000FC",
    "#0000BC",
    "#4428BC",
    "#940084",
    "#A80020",
    "#A81000",
    "#881400",
    "#503000",
    "#007800",
    "#006800",
    "#005800",
    "#004058",
    "#000000",
    "#000000",
    "#000000",
    "#BCBCBC",
    "#0078F8",
    "#0058F8",
    "#6844FC",
    "#D800CC",
    "#E40058",
    "#F83800",
    "#E45C10",
    "#AC7C00",
    "#00B800",
    "#00A800",
    "#00A844",
    "#008888",
    "#000000",
    "#000000",
    "#000000",
]

# Named colours used by the game. Change the look by changing these lines only.
COL_BG = "#000000"
COL_FLOOR = "#503000"
COL_CARD = "#BCBCBC"  # flip-board card face (must match scoreboard.png)
COL_CARD_EDGE = "#7C7C7C"
COL_MENU_DIM = "#7C7C7C"  # menu options that aren't selected
COL_PANEL = "#000000"  # menu box
COL_PANEL_BORDER = "#BCBCBC"
COL_GOLD = "#AC7C00"  # highlights: selected card, "You win!", unlocks
COL_PORTRAIT_BG = "#0000BC"  # square behind portraits on level cards
COL_KEY_RING = "#BCBCBC"  # blinking ring around the lit key hint

# ---------------------------------------------------------------------------
# Controls: index 0..3 = left edge, bottom left, bottom right, right edge
# ---------------------------------------------------------------------------
import pygame  # (needed for key constants)

HIT_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
KEY_LABELS = ["D", "F", "J", "K"]
POSITION_NAMES = ["left edge", "bottom left", "bottom right", "right edge"]

# Rules and timings (seconds) shared by every level.
# Per-level numbers (speed, hit window, points to win, ...) are in levels.py.
# ---------------------------------------------------------------------------
READY_TIME = 1.0  # pause before each serve
INTRO_TIME = 1.8  # first serve waits longer while the level name shows
POINT_PAUSE = 1.2  # pause after a point is scored
RESULT_DELAY = 1.5  # after the last point, wait this long before the result screen
EARLY_PRESS_IS_MISS = True

SERVE_POSITION = 1  # opponent always serves from top left
MISS_SHAKE = (3, 0.3)
RETURN_FLASH = 0.25

TRAIL_LENGTH = 10  # how many past ball positions a flaming/glowing trail follows
GLIDE_FRACTION = 0.8  # opponents who travel between spots take this share of your return to get there
# Each opponent's own numbers (smash, juggle, portals, rewind...) are at the top
# of their file in game/opponents/.

# Sound
SFX_VOLUME = 0.8  # all sound effects (0..1)
SFX_CHANNELS = 16  # how many sounds can play at once
RETURN_BOUNCE_AT = (
    0.55  # your return bounces on their half this far along its flight...
)
FAR_BOUNCE_VOLUME = 0.5  # ...a little quieter, being further away
MIXER = (
    44100,
    -16,
    2,
    256,
)  # rate, sample size, channels, buffer: a small buffer = sounds play without lag
# Per-sound loudness, for evening out sounds from different sources (1.0 = as recorded).
SOUND_VOLUMES = {
    "bounce": 0.8,
    "flip": 0.6,
    "menu_move": 0.6,
}

AMBIENCE_VOLUME = 0.5  # stage background loops, relative to the effects
AMBIENCE_FADE_MS = 800  # they fade in when a match starts and out when you leave

MUSIC_VOLUME = 0.5  # music on the title and level select (0..1)
MUSIC_MATCH_VOLUME = (
    0.35  # quieter in matches, so it never covers the hits you react to
)
MUSIC_FADE_OUT_MS = 0
MUSIC_FADE_IN_MS = 0
MUSIC_AFTER_JINGLE = 2.5  # seconds the win music waits for the match-won jingle

# HUD and feedback
KEY_PRESS_SHOW = 0.1  # how long a key icon shows as pressed
KEY_RING_BLINK = 4  # blinks per second of the ring around the lit key
BALL_SQUASH_TIME = 0.06  # squashed-ball frame when it bounces on your side
FLIP_TIME = 0.25  # flip-board card animation
MESSAGE_Y = 70  # where messages like "Too late!" appear
MENU_LINE = 12  # pixels between menu options
FIDGET_CHANCE = 0.25  # per second: opponents with a "fidget" animation (towel mop, hair flip) do it while waiting

# ---------------------------------------------------------------------------
# Table layout (internal pixels)
# ---------------------------------------------------------------------------
TABLE = (
    80,
    36,
    96,
    152,
)  # x, y, width, height (shorter so 32px sprites fit above and below)
NET_Y = TABLE[1] + TABLE[3] // 2

# Characters are placed by their feet (bottom-centre of the frame), so sprites of
# any size line up: the player's 40x40 frames stand on these points.
PLAYER_FEET = [(56, 176), (104, 224), (152, 224), (200, 176)]
# Opponents are placed by their feet (bottom-centre of the frame), so sprites of
# any size line up. At the far end they stand behind the table's far edge.
OPPONENT_FEET = [(56, 80), (104, 40), (152, 40), (200, 80)]

# Where the ball leaves the opponent, bounces on your half, and meets your paddle
OPPONENT_HIT = [(84, 64), (104, 40), (152, 40), (172, 64)]
PLAYER_BOUNCE = [(88, 160), (104, 172), (152, 172), (168, 160)]
PLAYER_HIT = [(76, 154), (110, 192), (158, 192), (192, 154)]

# Sprite positions for the art in assets/ (top-left corners, canvas pixels).
# table.png's blue surface starts 1px in, so it lines up exactly with TABLE.
TABLE_SPRITE_POS = (TABLE[0] - 1, TABLE[1] - 1)
NET_SPRITE_POS = (TABLE[0] - 5, NET_Y - 2)  # white tape sits on NET_Y
SCOREBOARD_POS = (0, 86)
KEY_ICON_POS = [(48, 178), (66, 200), (174, 200), (192, 178)]  # beside D F J K spots
BALL_SIZE = 7  # ball.png frames: ball, squashed ball, shadow

# Until opponents get their own art, they wear your sprite in a different kit.

# The telegraph rule: opponent position -> where the ball lands for you.
# Edges cross the table, bottom shots go straight.
LANDING_FOR = [3, 1, 2, 0]

BALL_ARC = 22  # peak height of the incoming shot, in pixels
WINDOW_ARC = 6  # small hop after the bounce


def resource_path(relative):
    """Find asset files both when run from source and from a PyInstaller exe."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = getattr(sys, "_MEIPASS", root)
    return os.path.join(base, relative)
