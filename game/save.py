"""Saving which levels you have beaten.

The save file lives in your user folder, not next to the game, because an
installed .exe may not be allowed to write to its own folder:
  Windows: %APPDATA%\\PingPongGod\\save.json
  macOS/Linux: ~/.local/share/PingPongGod/save.json
"""

import json
import os

from game.levels import LEVELS


def save_path():
    base = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "PingPongGod", "save.json")


class Progress:
    def __init__(self, beaten=None):
        # beaten[i] is True once level i has been won at least once.
        self.beaten = list(beaten or [])[: len(LEVELS)]
        self.beaten += [False] * (len(LEVELS) - len(self.beaten))

    def is_unlocked(self, index):
        """Level 0 is always open; every other level opens once the one before is beaten."""
        return index == 0 or self.beaten[index - 1]

    def next_to_play(self):
        """The first unlocked level you haven't beaten (or the last level if all are)."""
        for i in range(len(LEVELS)):
            if self.is_unlocked(i) and not self.beaten[i]:
                return i
        return len(LEVELS) - 1

    def mark_won(self, index):
        """Record a win. Returns True if this unlocked a new level."""
        newly_unlocked = not self.beaten[index] and index + 1 < len(LEVELS)
        self.beaten[index] = True
        save(self)
        return newly_unlocked


def load():
    """Read the save file. A missing or damaged file just means a fresh start."""
    try:
        with open(save_path(), encoding="utf-8") as f:
            data = json.load(f)
        return Progress([bool(b) for b in data.get("beaten", [])])
    except (OSError, ValueError, AttributeError, TypeError):
        return Progress()


def save(progress):
    """Write the save file. If that fails (read-only disk, ...), keep playing."""
    path = save_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"beaten": progress.beaten}, f)
        os.replace(tmp, path)  # swap in whole, so a crash can't leave half a file
    except OSError as err:
        print(f"Could not save progress: {err}")
