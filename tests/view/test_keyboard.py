from view.keyboard import read_char, KeyboardKey
from unittest.mock import MagicMock

def test_read_char_arrow_up(monkeypatch):
    seq = iter(["\x1b", "[", "A"])
    monkeypatch.setattr("sys.stdin.fileno", lambda: 0)
    monkeypatch.setattr("sys.stdin.read", lambda n: next(seq))
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", lambda fd, when, attr: None)
    monkeypatch.setattr("tty.setraw", lambda fd: None)
    
    token = read_char()
    assert token.key == KeyboardKey.UP


def test_read_char_char(monkeypatch):
    monkeypatch.setattr("sys.stdin.fileno", lambda: 0)
    monkeypatch.setattr("sys.stdin.read", lambda n: "x")
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", lambda fd, when, attr: None)
    monkeypatch.setattr("tty.setraw", lambda fd: None)
    
    token = read_char()
    assert token.key == KeyboardKey.CHAR and token.char == "x"


def test_read_char_mappings_all(monkeypatch):
    """read_char should return KeyboardToken for various inputs"""
    def mock_termios(*args, **kwargs):
        return None
    
    def mock_fileno():
        return 0
    
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", mock_termios)
    monkeypatch.setattr("tty.setraw", mock_termios)
    monkeypatch.setattr("sys.stdin.fileno", mock_fileno)
    
    # Arrow up
    seq = iter(["\x1b", "[", "A"])
    monkeypatch.setattr("sys.stdin.read", lambda n: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UP

    # Arrow down
    seq = iter(["\x1b", "[", "B"])
    monkeypatch.setattr("sys.stdin.read", lambda n: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.DOWN

    # Enter
    monkeypatch.setattr("sys.stdin.read", lambda n: "\r")
    token = read_char()
    assert token.key == KeyboardKey.ENTER

    # Space
    monkeypatch.setattr("sys.stdin.read", lambda n: " ")
    token = read_char()
    assert token.key == KeyboardKey.SPACE

    # Letter keys normalized to lowercase
    monkeypatch.setattr("sys.stdin.read", lambda n: "A")
    token = read_char()
    assert token.key == KeyboardKey.CHAR and token.char == "a"


def test_read_char_unknown_escapes(monkeypatch):
    """Unknown escape sequences should return UNKNOWN token"""
    def mock_termios(*args, **kwargs):
        return None
    
    def mock_fileno():
        return 0
    
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", mock_termios)
    monkeypatch.setattr("tty.setraw", mock_termios)
    monkeypatch.setattr("sys.stdin.fileno", mock_fileno)
    
    # Case 1: non-bracket following ESC
    seq = iter(["\x1b", "X", "Y"])
    monkeypatch.setattr("sys.stdin.read", lambda n: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UNKNOWN

    # Case 2: bracket but unsupported final byte
    seq = iter(["\x1b", "[", "C"])
    monkeypatch.setattr("sys.stdin.read", lambda n: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UNKNOWN


def test_read_char_backspace_variants(monkeypatch):
    def mock_termios(*args, **kwargs):
        return None
    
    def mock_fileno():
        return 0
    
    monkeypatch.setattr("termios.tcgetattr", lambda fd: [])
    monkeypatch.setattr("termios.tcsetattr", mock_termios)
    monkeypatch.setattr("tty.setraw", mock_termios)
    monkeypatch.setattr("sys.stdin.fileno", mock_fileno)
    
    # DEL (0x7f)
    monkeypatch.setattr("sys.stdin.read", lambda n: "\x7f")
    token = read_char()
    assert token.key == KeyboardKey.BACKSPACE

    # BACKSPACE
    monkeypatch.setattr("sys.stdin.read", lambda n: "\b")
    token = read_char()
    assert token.key == KeyboardKey.BACKSPACE
