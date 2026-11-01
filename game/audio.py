"""Sound effects, stage ambience and music.

    sfx.play("hit")      plays assets/sounds/hit.wav (or .ogg). If there are
                         numbered variants (hit_1.wav, hit_2.wav, ...) it picks
                         one at random, so repeated sounds don't feel copy-pasted.
    sfx.music("music_bot")  loops assets/music/music_bot.ogg, streamed from disk.

A sound that isn't there yet is simply skipped, so the game runs fine with an
incomplete set: drop new files into assets/sounds/ and they're used next launch.
"""

import array
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
        self._ambience = None  # the stage's background loop now playing (its name)
        self._music = None  # the track that's playing, or about to (its name)
        self._music_volume = S.MUSIC_VOLUME
        self._next = (
            None  # (name, volume, wait): starts once the old track has faded out
        )
        self._paused = False

    def init(self):
        """Start the mixer. Call before pygame.init() (pre_init) and after it (init)."""
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(S.SFX_CHANNELS)
            pygame.mixer.set_reserved(1)  # channel 0 is kept for the ambience loop
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

    @staticmethod
    def _tail(sound, seconds):
        """A copy of just the last `seconds` of a sound, with a 10 ms fade-in so it doesn't click."""
        mixer = pygame.mixer.get_init()
        if mixer is None:  # no audio device: nothing to trim
            return sound
        rate, size, channels = mixer
        frame = abs(size) // 8 * channels  # bytes per sample frame
        raw = sound.get_raw()
        keep = min(len(raw), int(seconds * rate) * frame)
        samples = array.array(
            "h", raw[len(raw) - keep :]
        )  # 16-bit samples (settings.MIXER)
        ramp = min(len(samples), int(0.01 * rate) * channels)
        for i in range(ramp):
            samples[i] = int(samples[i] * i / ramp)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name, volume=1.0, fallback=None, last=None):
        """Play a sound; returns its channel (to stop it early) or None.
        fallback: another sound to use if this one isn't there (e.g. "return" -> "hit").
        last: play only the final `last` seconds, so a build-up peaks right on time
              (BOT's charge whine peaks exactly as he fires, however long he charges)."""
        if not self.enabled or self.muted:
            return None
        variants = self._variants(name) or (
            self._variants(fallback) if fallback else []
        )
        if not variants:
            return None
        sound = random.choice(variants)
        if last is not None:
            sound = self._tail(sound, last)
        channel = sound.play()
        if channel is not None:
            channel.set_volume(volume * S.SFX_VOLUME * S.SOUND_VOLUMES.get(name, 1.0))
        return channel

    def ambience(self, name):
        """Loop a stage's background sound (crowd, waves, wind...) quietly under everything.
        Fades in; ambience(None) fades it out."""
        self._ambience = name
        if not self.enabled:
            return
        channel = pygame.mixer.Channel(0)
        if name is None or self.muted:
            channel.fadeout(S.AMBIENCE_FADE_MS)
            return
        variants = self._variants(name)
        if variants:
            loop = variants[0]
            loop.set_volume(
                S.AMBIENCE_VOLUME * S.SFX_VOLUME
            )  # on the sound: a channel's volume resets on play
            channel.play(loop, loops=-1, fade_ms=S.AMBIENCE_FADE_MS)

    # ---------------------------------------------------------------- music
    def music(self, name, volume=None, after=0.0):
        """Loop assets/music/<name>.ogg, streamed from disk.
        The old track fades out, then the new one fades in. Asking for the track
        that's already playing just keeps it going (at the new volume).
        after: wait this many seconds before starting (e.g. let a jingle finish).
        music(None) fades the music out."""
        volume = S.MUSIC_VOLUME if volume is None else volume
        if not self.enabled:
            return
        if name == self._music and self._next is None:
            self._music_volume = volume
            pygame.mixer.music.set_volume(0 if self.muted else volume)
            return
        self._music = name
        self._next = (name, volume, after) if name else None
        pygame.mixer.music.fadeout(S.MUSIC_FADE_OUT_MS)

    def _start_music(self, name, volume):
        path = S.resource_path(os.path.join("assets", "music", f"{name}.ogg"))
        if not os.path.exists(path):
            print(f"No music file {path}")
            return
        try:
            pygame.mixer.music.load(path)
        except pygame.error as err:
            print(f"Could not load {path}: {err}")
            return
        self._music_volume = volume
        pygame.mixer.music.set_volume(0 if self.muted else volume)
        pygame.mixer.music.play(loops=-1, fade_ms=S.MUSIC_FADE_IN_MS)

    def update(self, dt):
        """Call once a frame: starts the next track when the old one has faded out."""
        if not self.enabled or self._next is None or self._paused:
            return
        if pygame.mixer.music.get_busy():  # still fading out
            return
        name, volume, wait = self._next
        if wait > 0:
            self._next = (name, volume, wait - dt)
            return
        self._next = None
        self._start_music(name, volume)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            pygame.mixer.music.set_volume(0 if self.muted else self._music_volume)
        if self.muted and self.enabled:
            pygame.mixer.stop()
        elif self._ambience:
            self.ambience(self._ambience)  # back on: the stage's loop comes back too

    # The pause menu freezes sounds and music, and leaving a match stops the sounds.
    def pause(self):
        if self.enabled:
            pygame.mixer.pause()
            pygame.mixer.music.pause()
            self._paused = True

    def unpause(self):
        if self.enabled:
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()
            self._paused = False

    def stop_all(self):
        self._ambience = None
        if self.enabled:
            pygame.mixer.stop()
            self.unpause()  # the music carries on; the next scene picks its track


sfx = SoundEffects()
