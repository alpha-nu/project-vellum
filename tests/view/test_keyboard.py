from view.keyboard import read_char, KeyboardKey

def test_read_char_arrow_up(monkeypatch):
    seq = iter(["\x1b", "[", "A"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UP


def test_read_char_char(monkeypatch):
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: "x")
    token = read_char()
    assert token.key == KeyboardKey.CHAR and token.char == "x"


def test_read_char_mappings_all(monkeypatch):
    """read_char should return KeyboardToken for various inputs"""
    # Arrow up
    seq = iter(["\x1b", "[", "A"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UP

    # Arrow down
    seq = iter(["\x1b", "[", "B"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.DOWN

    # Enter
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: "\r")
    token = read_char()
    assert token.key == KeyboardKey.ENTER

    # Space
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: " ")
    token = read_char()
    assert token.key == KeyboardKey.SPACE

    # Letter keys normalized to lowercase
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: "A")
    token = read_char()
    assert token.key == KeyboardKey.CHAR and token.char == "a"


def test_read_char_unknown_escapes(monkeypatch):
    """Unknown escape sequences should return UNKNOWN token"""
    # Case 1: non-bracket following ESC
    seq = iter(["\x1b", "X", "Y"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UNKNOWN

    # Case 2: bracket but unsupported final byte
    seq = iter(["\x1b", "[", "C"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.UNKNOWN


def test_read_char_backspace_variants(monkeypatch):
    # DEL (0x7f)
    seq = iter(["\x7f"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.BACKSPACE

    # BACKSPACe
    seq = iter(["\b"])
    monkeypatch.setattr("view.keyboard.readchar.readchar", lambda: next(seq))
    token = read_char()
    assert token.key == KeyboardKey.BACKSPACE
