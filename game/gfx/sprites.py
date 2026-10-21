"""Loading Aseprite sprite sheets, recolouring them and playing animations.

Export from Aseprite with: File -> Export Sprite Sheet
  - Layout: Horizontal Strip
  - Output: Output File (name.png) + JSON Data (name.json), format "Array"
  - JSON meta: tick "Tags"

Each Aseprite tag becomes an animation (e.g. "idle", "ready", "swing_d"),
and each frame keeps the duration you set in Aseprite's timeline.
"""

import json
import os

import pygame

from game import settings as S


def load_image(*parts):
    """Load one image from assets/, e.g. load_image("ui", "keys.png")."""
    return pygame.image.load(
        S.resource_path(os.path.join("assets", *parts))
    ).convert_alpha()


def load_strip(path, frame_w):
    """Cut assets/<path> (a horizontal strip) into frames frame_w wide."""
    sheet = load_image(path)
    h = sheet.get_height()
    return [
        sheet.subsurface((x, 0, frame_w, h)).copy()
        for x in range(0, sheet.get_width() - frame_w + 1, frame_w)
    ]


def load_animations(name):
    """Load assets/<name>.png (+ .json) into {tag: [(surface, seconds), ...]}."""
    png = S.resource_path(os.path.join("assets", "sprites", f"{name}.png"))
    sheet = pygame.image.load(png).convert_alpha()

    jsn = S.resource_path(os.path.join("assets", "sprites", f"{name}.json"))
    data = {}
    if os.path.exists(jsn):
        with open(jsn, encoding="utf-8") as f:
            data = json.load(f)

    frames_data = data.get("frames", [])
    if isinstance(frames_data, dict):  # "Hash" export also works
        frames_data = list(frames_data.values())

    if frames_data:
        frames = [
            (
                sheet.subsurface(
                    pygame.Rect(
                        fr["frame"]["x"],
                        fr["frame"]["y"],
                        fr["frame"]["w"],
                        fr["frame"]["h"],
                    )
                ).copy(),
                max(fr.get("duration", 100), 10) / 1000,
            )
            for fr in frames_data
        ]
    else:
        # No JSON: cut the strip into square frames as tall as the image.
        size = sheet.get_height()
        frames = [
            (sheet.subsurface(pygame.Rect(x, 0, size, size)).copy(), 0.1)
            for x in range(0, sheet.get_width(), size)
        ]

    tags = data.get("meta", {}).get("frameTags", [])
    if tags:
        return {t["name"]: frames[t["from"] : t["to"] + 1] for t in tags}

    # Untagged sheet: frame 0 is idle, frames 1-4 are the swings for D F J K.
    anims = {"idle": frames[:1]}
    for i, key in enumerate("dfjk"):
        if len(frames) > i + 1:
            anims[f"swing_{key}"] = [frames[i + 1]]
    return anims


def recolour(anims, mapping):
    """Copy of anims with colours swapped, e.g. {"#004058": "#940084"}.

    Handy for giving the opponent a different kit before they get their own art.
    """
    out = {}
    for tag, frames in anims.items():
        new_frames = []
        for surf, dur in frames:
            surf = surf.copy()
            pixels = pygame.PixelArray(surf)
            for old, new in mapping.items():
                pixels.replace(pygame.Color(old), pygame.Color(new))
            del pixels  # unlock the surface
            new_frames.append((surf, dur))
        out[tag] = new_frames
    return out


class Animator:
    """Plays one animation at a time.

    loop(name)  - keep repeating an animation (idle, ready)
    play(name)  - play once, then go back to whatever was looping
    """

    def __init__(self, anims, start="idle"):
        self.anims = anims
        self.looping = start
        self.current = start
        self.once = False
        self.index = 0
        self.time = 0.0

    def _start(self, name, once):
        if name not in self.anims:  # missing art: just keep the idle pose
            name = "idle"
        self.current, self.once, self.index, self.time = name, once, 0, 0.0

    def play(self, name):
        self._start(name, once=True)

    def loop(self, name):
        if name not in self.anims:
            name = "idle"
        self.looping = name
        if not self.once and self.current != name:
            self._start(name, once=False)

    @property
    def busy(self):
        """True while a play-once animation (a swing) is running."""
        return self.once

    def update(self, dt):
        frames = self.anims[self.current]
        self.time += dt
        while self.time >= frames[self.index][1]:
            self.time -= frames[self.index][1]
            self.index += 1
            if self.index >= len(frames):
                if self.once:
                    self._start(self.looping, once=False)
                    frames = self.anims[self.current]
                else:
                    self.index = 0

    @property
    def image(self):
        return self.anims[self.current][self.index][0]
