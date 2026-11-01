"""The credits: the cast, then everyone whose music and sounds are in the game,
rolling up the screen over the ending theme.

Shown after beating the final boss, and from the title screen (C).
Enter/Esc skips; holding Down scrolls faster. Full links and licences are in CREDITS.md.
"""

import pygame

from game import controls
from game import settings as S
from game.audio import sfx
from game.gfx.sprites import load_image
from game.gfx.text import BitmapFont
from game.levels import LEVELS
from game.scenes.base import Scene

SCROLL_SPEED = 16  # pixels per second
FAST = 5  # holding Down scrolls this many times faster
HOLD_END = 4.0  # seconds "Thanks for playing" stays up before the credits close
LINE = 10  # pixels between lines
GAP = 20  # extra space before each section

# Names as they appear on the sites (the font shows them in capitals).
MUSIC = ["Juhani Junkala", "Cleyton Kauffman", "Great Boss author"]
OPENGAMEART = [
    "captaincrunch80",
    "Cough-E",
    "Ping pong sounds author",
    "Arr author",
    "Jingles author",
    "Rage author",
]
FREESOUND = [
    "al_sub",
    "ari_glitch",
    "audiopapkin",
    "bajko",
    "craigsmith",
    "creat142100",
    "cvltiv8r",
    "dblover",
    "dcsfx",
    "deraj",
    "dpren",
    "foad",
    "giddster",
    "gmgbeaumont",
    "hydroxian",
    "isaac200000",
    "jofae",
    "kentspublicdomain",
    "kyles",
    "lilmati",
    "mango777",
    "marlonnnnnn",
    "metaepitome",
    "pfannkuchn",
    "plasterbrain",
    "rinaldobowles56",
    "rosa-orenes256",
    "scorpion67890",
    "snapper4298",
    "werneristes",
]
TOOLS = ["pygame-ce", "ModernGL", "Aseprite", "PyInstaller"]


class CreditsScene(Scene):
    def __init__(self, then, revealed=False):
        """then: a function returning the scene to go to afterwards.
        revealed: show the final boss's true name in the cast (you've beaten him)."""
        self.font = BitmapFont()
        self.then = then
        self.items = []  # (y, kind, payload): kind is "text" or "face"
        self.height = 0
        self._build(revealed)
        self.offset = 0.0  # how far the roll has scrolled up
        self.end = self.height - LINE + S.HEIGHT // 2  # the last line rests mid-screen
        self.hold = 0.0
        sfx.music("music_ending")

    # ------------------------------------------------------------------ layout
    def _text(self, text, color=None, space=LINE):
        self.items.append((self.height, "text", (text, color)))
        self.height += space

    def _section(self, title):
        self.height += GAP
        self._text(title, S.COL_GOLD, LINE + 4)

    def _names(self, names):
        """Two names to a line, so long lists don't drag."""
        for i in range(0, len(names), 2):
            self._text("   ".join(names[i : i + 2]))

    def _build(self, revealed):
        self._text("Ping Pong God", S.COL_GOLD, LINE + 4)
        self._text("A game by Clyde Mugambi")
        self._text("Code, art and design", S.COL_MENU_DIM)

        self._section("Starring")
        cast = [("portrait", "You")]
        for i, level in enumerate(LEVELS):
            last = i == len(LEVELS) - 1
            name = (
                level.true_name
                if (last and revealed and level.true_name)
                else level.opponent
            )
            if level.portrait:
                cast.append((level.portrait, name))
        for portrait, name in cast:
            face = load_image("sprites", f"{portrait}.png")
            self.items.append((self.height, "face", face))
            self.height += face.get_height() + 4
            self._text(name, space=LINE + 8)

        self._section("Music")
        self._names(MUSIC)
        self._section("Sound effects")
        self._text("From OpenGameArt.org", S.COL_MENU_DIM)
        self._names(OPENGAMEART)
        self.height += LINE // 2
        self._text("From Freesound.org", S.COL_MENU_DIM)
        self._names(FREESOUND)
        self.height += LINE // 2
        self._text(
            "SFX_Explosion_14 by jalastram"
        )  # CC BY 4.0: title, author, link, licence
        self._text("freesound.org/s/317767 (CC BY 4.0)", S.COL_MENU_DIM)
        self._section("Built with")
        self._names(TOOLS)
        self._section("Sources and licences")
        self._text("See CREDITS.md", S.COL_MENU_DIM)
        self.height += GAP * 3
        self._text("Thanks for playing!", S.COL_GOLD)

    # ------------------------------------------------------------------ scene
    def _finish(self):
        if self.app:
            self.app.switch(self.then())

    def handle_event(self, event):
        if controls.pressed(event, controls.CONFIRM + controls.BACK):
            self._finish()

    def update(self, dt):
        if self.offset < self.end:
            fast = any(pygame.key.get_pressed()[k] for k in controls.DOWN)
            self.offset = min(
                self.end, self.offset + SCROLL_SPEED * (FAST if fast else 1) * dt
            )
        else:
            self.hold += dt
            if self.hold >= HOLD_END:
                self._finish()

    def draw(self, surf):
        surf.fill(S.COL_BG)
        top = S.HEIGHT - round(self.offset)  # the roll starts just below the screen
        for y, kind, payload in self.items:
            sy = top + y
            if sy < -40 or sy > S.HEIGHT:
                continue
            if kind == "face":
                surf.blit(payload, payload.get_rect(midtop=(S.WIDTH // 2, sy)))
            else:
                text, color = payload
                self.font.draw(surf, text, (S.WIDTH // 2, sy), color=color)
