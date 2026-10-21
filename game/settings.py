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

# ---------------------------------------------------------------------------
# Controls: index 0..3 = left edge, bottom left, bottom right, right edge
# ---------------------------------------------------------------------------
import pygame  # noqa: E402  (needed for key constants)

HIT_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
KEY_LABELS = ["D", "F", "J", "K"]
POSITION_NAMES = ["left edge", "bottom left", "bottom right", "right edge"]

# ---------------------------------------------------------------------------
# Rules and timings (seconds). These are the numbers we'll tune per level.
# ---------------------------------------------------------------------------
POINTS_TO_WIN = 3
READY_TIME = 1.0  # pause before each serve
WINDUP_TIME = 0.25  # opponent stands at a spot before hitting (the telegraph)
FLY_TIME = 0.9  # ball travel from opponent to the bounce on your half
HIT_WINDOW = 0.45  # time after the bounce in which you must press
RETURN_TIME = 0.7  # your return travelling back to the opponent
POINT_PAUSE = 1.2  # pause after a point is scored
EARLY_PRESS_IS_MISS = True
OPPONENT_MISS_CHANCE = 0.2  # tutorial opponent misses 1 in 5 of your returns

SERVE_POSITION = 1  # opponent always serves from top left
MISS_SHAKE = (3, 0.3)
RETURN_FLASH = 0.25

# HUD and feedback
KEY_HINTS = True  # light the key for the incoming shot (tutorial)
KEY_HINT_RETURNS = (
    5  # stop lighting after this many returns in a match; None = never stop
)
KEY_PRESS_SHOW = 0.1  # how long a key icon shows as pressed
BALL_SQUASH_TIME = 0.06  # squashed-ball frame when it bounces on your side
FLIP_TIME = 0.25  # flip-board card animation
MESSAGE_Y = 70  # where messages like "Too late!" appear
MENU_LINE = 12  # pixels between menu options

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

# Sprites: 32x32 frames from Aseprite, animations named by tags (see sprites.py).
SPRITE_SIZE = 32

# Where the centre of each sprite stands at each of the 4 positions
PLAYER_STAND = [(56, 160), (104, 208), (152, 208), (200, 160)]
OPPONENT_STAND = [(56, 64), (104, 16), (152, 16), (200, 64)]

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
OPPONENT_KIT = {"#004058": "#940084", "#E45C10": "#00A844", "#F83800": "#00B800"}

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
