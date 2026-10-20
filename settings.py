"""Game-wide settings: screen, palette, controls, timings and table layout.

Everything you'll want to tune lives here, so gameplay tweaks never mean
digging through the match code.
"""

import os
import sys

# FOR THE SCREEN
TITLE = "Ping Pong God (prototype)"
WIDTH, HEIGHT = 256, 224
SCALE = 3
FPS = 60

# Palette, NES STYLE
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

# Named colours used by the game.
COL_BG = "#000000"
COL_FLOOR = "#503000"
COL_TABLE = "#0058F8"
COL_LINES = "#BCBCBC"
COL_NET = "#BCBCBC"
COL_SHADOW = "#0000BC"
COL_BALL = "#E45C10"
COL_PLAYER = "#F83800"
COL_OPPONENT = "#6844FC"
COL_PADDLE = "#A80020"
COL_TEXT = "#BCBCBC"
COL_HIGHLIGHT = "#AC7C00"

# Controls: index 0..3 = left edge, bottom left, bottom right, right edge
import pygame

HIT_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
KEY_LABELS = ["D", "F", "J", "K"]
POSITION_NAMES = ["left edge", "bottom left", "bottom right", "right edge"]

# Rules and timing setting. To be tuned per level
POINTS_TO_WIN = 3
READY_TIME = 1.0  # pause before each serve
WINDUP_TIME = 0.25  # opponent stands at a spot before hitting (the telegraph)
FLY_TIME = 0.9  # ball travel from opponent to the bounce on your half
HIT_WINDOW = 0.45  # time after the bounce in which you must press
RETURN_TIME = 0.7  # your return travelling back to the opponent
POINT_PAUSE = 1.2  # pause after a point is scored
SWING_TIME = 0.15  # how long the swing pose shows
EARLY_PRESS_IS_MISS = True
OPPONENT_MISS_CHANCE = 0.2  # tutorial opponent misses 1 in 5 of your returns

SERVE_POSITION = 1  # opponent always serves from top left

# Table Layout
TABLE = (80, 24, 96, 176)
NET_Y = TABLE[1] + TABLE[3] // 2

# Where the sprites stand at each of the 4 positions
PLAYER_STAND = [(56, 160), (104, 212), (152, 212), (200, 160)]
OPPONENT_STAND = [(56, 64), (104, 12), (152, 12), (200, 64)]

# Where the ball leaves the opponent, bounces on your half, and meets your paddle
OPPONENT_HIT = [(84, 64), (104, 28), (152, 28), (172, 64)]
PLAYER_BOUNCE = [(88, 160), (104, 180), (152, 180), (168, 160)]
PLAYER_HIT = [(70, 160), (104, 204), (152, 204), (186, 160)]

# The telegraph rule: opponent position -> where the ball lands for you.
# Edges cross the table, bottom shots go straight.
LANDING_FOR = [3, 1, 2, 0]

BALL_ARC = 22  # peak height of the incoming shot, in pixels
WINDOW_ARC = 6  # small hop after the bounce


def resource_path(relative):
    """Find asset files both when run from source and from a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)
