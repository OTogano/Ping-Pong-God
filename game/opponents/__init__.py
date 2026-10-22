"""Every opponent's tricks, one file each. A level names its opponent with `kind`."""

from game.opponents.base import Opponent
from game.opponents.bot import Bot
from game.opponents.esmeralda import Esmeralda
from game.opponents.greg import Greg
from game.opponents.odin import Odin
from game.opponents.squidy import Squidy

KINDS = {
    "greg": Greg,
    "esmeralda": Esmeralda,
    "squidy": Squidy,
    "bot": Bot,
    "odin": Odin,
}


def make_opponent(match):
    """The opponent for this match's level (a plain Opponent if the level names none)."""
    return KINDS.get(match.level.kind or "", Opponent)(match)
