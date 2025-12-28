from enum import Enum, auto
from dataclasses import dataclass
import readchar
from typing import Optional


class KeyboardKey(Enum):
    UP = auto()
    DOWN = auto()
    ENTER = auto()
    SPACE = auto()
    CHAR = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class KeyboardToken:
    key: KeyboardKey
    char: Optional[str] = None


def read_char() -> KeyboardToken:
    """Read keys from `readchar` and return a KeyboardToken with an enum key.

    Handles ANSI escape sequences for arrow keys and normalizes single characters
    to lowercase.
    """
    ch = readchar.readchar()
    if ch == "\x1b":
        # Potential escape sequence
        next1 = readchar.readchar()
        next2 = readchar.readchar()
        if next1 == "[":
            if next2 == "A":
                return KeyboardToken(KeyboardKey.UP)
            if next2 == "B":
                return KeyboardToken(KeyboardKey.DOWN)
        return KeyboardToken(KeyboardKey.UNKNOWN)

    if ch in ("\r", "\n"):
        return KeyboardToken(KeyboardKey.ENTER)
    if ch == " ":
        return KeyboardToken(KeyboardKey.SPACE)
    # Regular character
    return KeyboardToken(KeyboardKey.CHAR, ch.lower())