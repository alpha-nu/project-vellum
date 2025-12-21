import pytest
from rich.console import Console
from pathlib import Path

from view.ui import RetroCLI


def test_retrocli_basic_rendering(tmp_path):
    console = Console(record=True)
    ui = RetroCLI(console=console)

    # Should not raise
    ui.draw_header()
    ui.print_panel("hello world")
    ui.show_error("something went wrong")
    ui.show_no_files()
    ui.show_merge_complete("out.txt")
    ui.show_shutdown(1.23)

    text = console.export_text()
    assert len(text) > 0
    assert "hello world" in text or "something went wrong" in text
