"""Sound effects.

    sfx.play("hit")      plays assets/sounds/hit.wav (or .ogg). If there are
                         numbered variants (hit_1.wav, hit_2.wav, ...) it picks
                         one at random, so repeated sounds don't feel copy-pasted.

A sound that isn't there yet is simply skipped, so the game runs fine with an
incomplete set: drop new files into assets/sounds/ and they're used next launch.
"""

import glob
import os
import random

import pygame

from game import settings as S


class SoundEffects:
    def __init__(self):
        self.enabled = False  # False if there's no audio device (the game still runs)
        self.muted = False
        self._sounds = {}  # name -> list of variants (empty list = not found)

    def init(self):
        """Start the mixer. Call before pygame.init() (pre_init) and after it (init)."""
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(S.SFX_CHANNELS)
            self.enabled = True
            folder = S.resource_path(os.path.join("assets", "sounds"))
            found = glob.glob(os.path.join(folder, "*.wav")) + glob.glob(
                os.path.join(folder, "*.ogg")
            )
            print(f"Sounds: {len(found)} files in {folder}")
        except pygame.error as err:
            print(f"No sound ({err}); playing silently.")

    def _variants(self, name):
        if name not in self._sounds:
            folder = S.resource_path(os.path.join("assets", "sounds"))
            files = []
            for ext in ("wav", "ogg"):
                files += glob.glob(os.path.join(folder, f"{name}.{ext}"))
                files += glob.glob(os.path.join(folder, f"{name}_[0-9]*.{ext}"))
            sounds = []
            for path in sorted(files):
                try:
                    sounds.append(pygame.mixer.Sound(path))
                except pygame.error as err:
                    print(f"Could not load {path}: {err}")
            self._sounds[name] = sounds
        return self._sounds[name]

    def play(self, name, volume=1.0, fallback=None):
        """Play a sound; returns its channel (to stop it early) or None.
        fallback: another sound to use if this one isn't there (e.g. "return" -> "hit")."""
        if not self.enabled or self.muted:
            return None
        variants = self._variants(name) or (
            self._variants(fallback) if fallback else []
        )
        if not variants:
            return None
        sound = random.choice(variants)
        channel = sound.play()
        if channel is not None:
            channel.set_volume(volume * S.SFX_VOLUME * S.SOUND_VOLUMES.get(name, 1.0))
        return channel

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted and self.enabled:
            pygame.mixer.stop()

    # The pause menu freezes sounds that are still playing, and leaving a match stops them.
    def pause(self):
        if self.enabled:
            pygame.mixer.pause()

    def unpause(self):
        if self.enabled:
            pygame.mixer.unpause()

    def stop_all(self):
        if self.enabled:
            pygame.mixer.stop()
            pygame.mixer.unpause()


sfx = SoundEffects()
