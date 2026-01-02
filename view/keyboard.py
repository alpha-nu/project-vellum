import sys
import tty
import termios
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class KeyboardKey(Enum):
    UP = auto()
    DOWN = auto()
    ENTER = auto()
    SPACE = auto()
    BACKSPACE = auto()
    CHAR = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class KeyboardToken:
    key: KeyboardKey
    char: Optional[str] = None



def read_char():
    """Reads a single character from stdin without waiting for Enter."""
    fd = sys.stdin.fileno()
    attr = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            next1 = sys.stdin.read(1)
            next2 = sys.stdin.read(1)
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
        if ch in ("\x7f", "\b"):
            return KeyboardToken(KeyboardKey.BACKSPACE)
        return KeyboardToken(KeyboardKey.CHAR, ch.lower())
    
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, attr)
