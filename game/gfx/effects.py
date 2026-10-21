"""Screen effects that any scene can trigger, e.g. `fx.shake(3, 0.25)`.

The renderer reads these values every frame and passes them to the shaders.
"""

import random


class Effects:
    def __init__(self):
        self.crt = False
        self._shake_strength = 0.0
        self._shake_time = 0.0
        self._shake_left = 0.0
        self.flash_amount = 0.0
        self.flash_color = (1.0, 1.0, 1.0)
        self._flash_fade = 1.0
        self.offset = (0.0, 0.0)

    def shake(self, strength=3.0, duration=0.25):
        """Shake the screen by up to `strength` canvas pixels, fading out."""
        self._shake_strength = strength
        self._shake_time = self._shake_left = duration

    def flash(self, amount=0.5, duration=0.12, color="#BCBCBC"):
        """Briefly tint the whole screen toward `color`."""
        c = color.lstrip("#")
        self.flash_color = tuple(int(c[i : i + 2], 16) / 255 for i in (0, 2, 4))
        self.flash_amount = amount
        self._flash_fade = amount / duration

    def update(self, dt):
        if self._shake_left > 0:
            self._shake_left = max(0.0, self._shake_left - dt)
            s = self._shake_strength * (self._shake_left / self._shake_time)
            # Whole pixels only, so the pixel art never looks blurry.
            self.offset = (round(random.uniform(-s, s)), round(random.uniform(-s, s)))
        else:
            self.offset = (0.0, 0.0)
        self.flash_amount = max(0.0, self.flash_amount - self._flash_fade * dt)


fx = Effects()
