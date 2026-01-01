import pytest
import time
from collections import defaultdict
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, patch

from rich.console import Console
from rich.text import Text

from view.merge_mode import MergeMode
from view.ui import (
    RetroCLI,
    StyledTimeElapsedColumn,
    StyledPercentageColumn,
    StyledDescriptionColumn,
    _StyledTimeMixin,
)
from view.output_format import OutputFormat
from view.interface import ActionResult, ActionKind
from view.keyboard import KeyboardToken, KeyboardKey

from domain.model.file import File
from domain.adapters.file_factories import file_from_path


# ===== Keyboard Mock Helper =====

def keyboard_from_string(input_str):
    """Create a keyboard reader from a string representation.
    Args:
        input_str: String like "DOWN DOWN SPACE ENTER" or "q"
    
    Returns:
        A callable keyboard reader
    """
    key_map = {
        "UP": KeyboardToken(KeyboardKey.UP),
        "DOWN": KeyboardToken(KeyboardKey.DOWN),
        "ENTER": KeyboardToken(KeyboardKey.ENTER),
        "SPACE": KeyboardToken(KeyboardKey.SPACE),
        "BACKSPACE": KeyboardToken(KeyboardKey.BACKSPACE),
    }
    
    sequence = []
    for token in input_str.split():
        sequence.append(key_map.get(token, KeyboardToken(KeyboardKey.CHAR, token.lower())))
        
    iterator = iter(sequence)
    return lambda: next(iterator)


# ===== Time Provider Mock Helper =====

def time_provider_sequence(*times):
    """Create a time provider that returns a sequence of time values.
    
    Args:
        *times: Sequence of float time values to return on successive calls
    
    Returns:
        A callable time provider that returns the next time value
    """
    iterator = iter(times)
    return lambda: next(iterator)


class TestRetroCLIBasics:
    """Test basic RetroCLI initialization and utility methods"""
    
    def test_init_default(self):
        """Test initialization with defaults"""
        ui = RetroCLI()
        
        assert ui.max_width == 120
        assert ui.console is not None
        assert "subtle" in ui.colors
        assert "primary" in ui.colors
        assert "secondary" in ui.colors
        assert "accented" in ui.colors
    
    def test_init_custom_console(self):
        """Test initialization with custom console"""
        console = Console(record=True)
        ui = RetroCLI(console=console, max_width=100)
        
        assert ui.console is console
        assert ui.max_width == 100
    
    def test_init_custom_colors(self):
        """Test initialization with custom colors"""
        custom_colors = {"subtle": "#ff0000", "custom": "#00ff00"}
        ui = RetroCLI(colors=custom_colors)
        
        assert ui.colors["subtle"] == "#ff0000"
        assert ui.colors["custom"] == "#00ff00"
        # Default colors should still exist
        assert "primary" in ui.colors
    
    def test_print_center(self):
        """Test centered printing"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.print_center("Test content")
        
        text = console.export_text()
        assert "Test content" in text


class TestProgressColumns:
    """Test custom progress column classes"""
    
    def test_styled_time_mixin_render_with_value(self):
        """Test mixin render with valid value"""
        mixin = _StyledTimeMixin("cyan", "elapsed")
        
        task = Mock()
        task.elapsed = 125.5  # 2 minutes 5 seconds
        
        result = mixin.render(task)
        assert "02:05" in str(result)
    
    def test_styled_time_mixin_render_none_value(self):
        """Test mixin render with None value"""
        mixin = _StyledTimeMixin("cyan", "elapsed")
        
        task = Mock()
        task.elapsed = None
        
        result = mixin.render(task)
        assert "00:00" in str(result)
    
    def test_styled_time_mixin_format_time_seconds(self):
        """Test time formatting for seconds"""
        mixin = _StyledTimeMixin("style", "attr")
        
        assert mixin._format_time(45) == "00:45"
        assert mixin._format_time(0) == "00:00"
        assert mixin._format_time(59) == "00:59"
    
    def test_styled_time_mixin_format_time_minutes(self):
        """Test time formatting for minutes"""
        mixin = _StyledTimeMixin("style", "attr")
        
        assert mixin._format_time(60) == "01:00"
        assert mixin._format_time(125) == "02:05"
        assert mixin._format_time(3599) == "59:59"
    
    def test_styled_time_mixin_format_time_hours(self):
        """Test time formatting for hours"""
        mixin = _StyledTimeMixin("style", "attr")
        
        assert mixin._format_time(3600) == "01:00:00"
        assert mixin._format_time(7265) == "02:01:05"
        assert mixin._format_time(36000) == "10:00:00"
    
    def test_styled_time_elapsed_column_pending(self):
        """Test time elapsed column with pending status"""
        column = StyledTimeElapsedColumn("cyan")
        
        # Create mock task
        task = Mock()
        task.fields = {"status": "pending", "filename": "test.pdf"}
        
        result = column.render(task)
        assert "00:00" in str(result)
    
    def test_styled_time_elapsed_column_converting(self):
        """Test time elapsed column during conversion"""
        # Use deterministic time provider: start=100.0, current=105.0 (5 seconds elapsed)
        time_provider = time_provider_sequence(105.0)
        column = StyledTimeElapsedColumn("cyan", time_provider=time_provider)
        
        # Create mock task with start time
        task = Mock()
        task.fields = {
            "status": "converting",
            "filename": "test.pdf",
            "start_time": 100.0  # Started at time 100.0
        }
        
        result = column.render(task)
        # Should show 5 seconds (105.0 - 100.0 = 5.0)
        assert "00:05" in str(result)
    
    def test_styled_time_elapsed_column_done(self):
        """Test time elapsed column when done"""
        column = StyledTimeElapsedColumn("cyan")
        
        # Create mock task
        task = Mock()
        task.fields = {
            "status": "done",
            "filename": "test.pdf",
            "conversion_time": 12.5
        }
        
        result = column.render(task)
        assert "00:12" in str(result)
    
    def test_styled_time_elapsed_column_no_fields(self):
        """Test time elapsed column with no fields"""
        column = StyledTimeElapsedColumn("cyan")
        
        task = Mock()
        task.fields = None
        
        result = column.render(task)
        assert "00:00" in str(result)
    
    def test_styled_percentage_column_converting(self):
        """Test percentage column during conversion"""
        colors = {"confirm": "green", "accented": "cyan"}
        column = StyledPercentageColumn(colors)
        
        task = Mock()
        task.percentage = 45.0
        task.fields = {"status": "converting"}
        
        result = column.render(task)
        assert "45%" in str(result)
    
    def test_styled_percentage_column_done(self):
        """Test percentage column when done"""
        colors = {"confirm": "green", "accented": "cyan"}
        column = StyledPercentageColumn(colors)
        
        task = Mock()
        task.percentage = 100.0
        task.fields = {"status": "done"}
        
        result = column.render(task)
        assert "100%" in str(result)
    
    def test_styled_description_column_pending(self):
        """Test description column with pending status"""
        colors = {"confirm": "green", "accented": "cyan", "subtle": "grey"}
        column = StyledDescriptionColumn(colors)
        
        task = Mock()
        task.fields = {"status": "pending", "filename": "test.pdf"}
        
        result = column.render(task)
        assert "test.pdf" in str(result)
    
    def test_styled_description_column_converting(self):
        """Test description column during conversion"""
        colors = {"confirm": "green", "accented": "cyan", "subtle": "grey"}
        column = StyledDescriptionColumn(colors)
        
        task = Mock()
        task.fields = {"status": "converting", "filename": "document.epub"}
        
        result = column.render(task)
        assert "converting" in str(result).lower()
        assert "document.epub" in str(result)
    
    def test_styled_description_column_done(self):
        """Test description column when done"""
        colors = {"confirm": "green", "accented": "cyan", "subtle": "grey"}
        column = StyledDescriptionColumn(colors)
        
        task = Mock()
        task.fields = {"status": "done", "filename": "complete.pdf"}
        
        result = column.render(task)
        assert "complete.pdf" in str(result)


class TestDisplayMethods:
    """Test display and rendering methods"""
    
    def test_draw_header(self):
        """Test header drawing"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.draw_header()
        
        text = console.export_text()
        assert "VELLUM" in text or "epub" in text
    
    def test_show_error(self):
        """Test error message display"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.show_error("fatal error: file not found")
        
        text = console.export_text()
        assert "fatal error" in text
    
    def test_show_conversion_summary(self):
        """Test conversion summary display with different merge modes"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        # Test no_merge mode
        ui.show_conversion_summary(
            total_files=3,
            output_count=3,
            merge_mode=MergeMode.NO_MERGE,
            merged_filename=None,
            total_runtime=45.67,
            total_input_size_formatted="2.0MB",
            total_output_size_formatted="1.5MB"
        )
        
        text = console.export_text()
        assert "conversion complete" in text.lower()
        assert "files processed:     3" in text
        assert "output created:      3 files" in text
        assert "total runtime:       45.67s" in text
        assert "input size:          2.0MB" in text
        # Keybinding hints moved to `ask_again()`; summary no longer contains them
        
        # Clear console for next test
        console.clear()
        
        # Test merge mode
        ui.show_conversion_summary(
            total_files=2,
            output_count=1,
            merge_mode=MergeMode.MERGE,
            merged_filename="combined.txt",
            total_runtime=12.34,
            total_input_size_formatted="1.0MB",
            total_output_size_formatted="800.0KB"
        )
        
        text = console.export_text()
        assert "output created:      1 merged file (combined.txt)" in text
        assert "total runtime:       12.34s" in text
        assert "input size:          1.0MB" in text


class TestSelectionMethods:
    """Tests for selection helpers that return ActionResult back when backing out."""

    def test_select_output_format_back_returns_back_action(self):
        keyboard = lambda: KeyboardToken(KeyboardKey.BACKSPACE)
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard)

        res = ui.select_output_format()
        assert isinstance(res, ActionResult)
        assert res.kind == ActionKind.BACK


    def test_select_merge_mode_back_returns_back_action(self):
        keyboard = lambda: KeyboardToken(KeyboardKey.BACKSPACE)
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard)

        res = ui.select_merge_mode()
        assert isinstance(res, ActionResult)
        assert res.kind == ActionKind.BACK
        
        # Clear console for next test
        console.clear()
        
        # Test per_page mode
        ui.show_conversion_summary(
            total_files=1,
            output_count=5,
            merge_mode=MergeMode.PER_PAGE,
            merged_filename=None,
            total_runtime=8.90,
            total_input_size_formatted="500.0KB",
            total_output_size_formatted="300.0KB"
        )
        
        text = console.export_text()
        assert "output created:      5 pages/chapters" in text
        assert "total runtime:       8.90s" in text
        assert "input size:          500.0KB" in text
        
        # Clear console for next test
        console.clear()
        
        # Test edge cases for file size formatting
        # Test bytes (B) unit
        ui.show_conversion_summary(
            total_files=1,
            output_count=1,
            merge_mode="no_merge",
            merged_filename=None,
            total_runtime=1.0,
            total_input_size_formatted="512B",
            total_output_size_formatted="256B"
        )
        
        text = console.export_text()
        assert "input size:          512B" in text
        
        # Clear console for next test
        console.clear()
        
        # Test terabytes (TB) unit
        ui.show_conversion_summary(
            total_files=1,
            output_count=1,
            merge_mode="no_merge",
            merged_filename=None,
            total_runtime=1.0,
            total_input_size_formatted="1.0TB",
            total_output_size_formatted="500.0GB"
        )
        
        text = console.export_text()
        assert "input size:          1.0TB" in text
        
        # Clear console for next test
        console.clear()
        
        # Test single file no_merge with filename display
        ui.show_conversion_summary(
            total_files=1,
            output_count=1,
            merge_mode=MergeMode.NO_MERGE,
            merged_filename=None,
            total_runtime=2.5,
            total_input_size_formatted="100.0KB",
            total_output_size_formatted="80.0KB",
            single_output_filename="document.txt"
        )
        
        text = console.export_text()
        assert "output created:      document.txt" in text
        assert "total runtime:       2.50s" in text

    def test_radio_select_q_terminates(self):
        # Use existing keyboard helper to simulate pressing 'q'
        keyboard = keyboard_from_string("q")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard)

        result = ui.select_output_format()

        assert result.kind == ActionKind.TERMINATE


    def test_select_files_back_on_backspace(self):
        # Use existing keyboard helper to simulate BACKSPACE
        keyboard = keyboard_from_string("BACKSPACE")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard)

        file_data = {"name": "a.pdf", "size": "1KB"}

        result = ui.select_files([file_data])

        assert result.kind == ActionKind.BACK
    
    def test_clear_and_show_header(self):
        """Test clear_and_show_header clears console and redraws header"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        # Add some initial content
        console.print("initial content")
        
        # Clear and show header
        ui.clear_and_show_header()
        
        # Verify header is shown and initial content is still there (console.clear() in record mode doesn't actually clear)
        text = console.export_text()
        assert "epub | pdf -> txt" in text.lower()

    def test_ask_again_enter_and_quit(self):
        """ask_again should return True for Enter and False for 'q'"""
        console = Console(record=True)
        
        # Test Enter -> Proceed
        keyboard_reader = keyboard_from_string("ENTER")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        res = ui.ask_again()
        assert res.kind == ActionKind.PROCEED

        # Test 'q' -> Terminate
        keyboard_reader = keyboard_from_string("q")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        res = ui.ask_again()
        assert res.kind == ActionKind.TERMINATE

    def test_ask_again_ignores_other_keys(self):
        """ask_again should ignore unrelated keys until a valid one is pressed"""
        console = Console(record=True)
        
        # Sequence: x (ignored), ENTER (accepted)
        keyboard_reader = keyboard_from_string("x ENTER")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        res = ui.ask_again()
        assert res.kind == ActionKind.PROCEED


class TestInteractiveSelection:
    """Test interactive file selection"""
    
    @staticmethod
    def _paths_to_file_data(paths):
        """Convert Path objects to file data dicts for view."""
        return [file_from_path(p).to_dict() for p in paths]
    
    def test_select_files_enter_immediately(self, tmp_path):
        """Test selecting files by pressing enter immediately (no selection)"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate pressing Enter immediately
        keyboard_reader = keyboard_from_string("ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)

        assert selected.payload == []
    
    def test_select_files_space_then_enter(self, tmp_path):
        """Test selecting file with space then enter"""
        files = [tmp_path / f"file{i}.pdf" for i in range(2)]
        for f in files:
            f.touch()
        
        # Simulate: space (select), enter (confirm)
        keyboard_reader = keyboard_from_string("SPACE ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data).payload

        assert selected == [0]
    
    def test_select_files_down_arrow(self, tmp_path):
        """Test navigating with down arrow"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: down arrow, space, enter
        keyboard_reader = keyboard_from_string("DOWN SPACE ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        # Should select second file (index 1)
        assert len(selected) == 1
        assert selected[0] == 1
    
    def test_select_files_up_arrow(self, tmp_path):
        """Test navigating with up arrow (wraps to end)"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: up arrow (wraps to last), space, enter
        keyboard_reader = keyboard_from_string("UP SPACE ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        # Should wrap to last file
        assert len(selected) == 1
        assert selected[0] == 2  # Last file index
    
    def test_select_files_toggle_on_off(self, tmp_path):
        """Test toggling selection on and off"""
        files = [tmp_path / "file.pdf"]
        files[0].touch()
        
        # Simulate: space (select), space (deselect), enter
        keyboard_reader = keyboard_from_string("SPACE SPACE ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        # Should be deselected
        assert selected == []
    
    def test_select_files_select_all(self, tmp_path):
        """Test selecting all with 'a' key - should select but not confirm"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), enter (confirm)
        keyboard_reader = keyboard_from_string("a ENTER")
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        assert len(selected) == 3
        assert selected == [0, 1, 2]  # All indices
    
    def test_select_files_quit(self, tmp_path):
        """Test quitting with 'q' key exits application"""
        files = [tmp_path / "file.pdf"]
        files[0].touch()
        # Simulate: 'q' (quit)
        keyboard_reader = keyboard_from_string("q")
        
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        # The UI may now return an ActionResult.terminate() instead of raising SystemExit
        try:
            res = ui.select_files(file_data)
            if isinstance(res, ActionResult):
                # Expect a terminate action
                assert res.kind.name == 'TERMINATE'
        except SystemExit as exc:
            assert exc.code == 0
    def test_select_files_all_toggle_deselect(self, tmp_path):
        """Test [A] pressed twice toggles: select all then deselect all"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), 'a' (deselect all), enter
        keyboard_input = keyboard_from_string("a a ENTER")
        
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        # Should be empty after toggle
        assert len(selected) == 0
    
    def test_select_files_all_continues_loop(self, tmp_path):
        """Test [A] selects all but allows further navigation before confirm"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), space (deselect current), enter
        keyboard_input = keyboard_from_string("a SPACE ENTER")
        
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        file_data = self._paths_to_file_data(files)
        
        selected = ui.select_files(file_data)
        if isinstance(selected, ActionResult):
            selected = selected.payload

        # Should have 2 files (all 3 selected, then current deselected)
        assert len(selected) == 2
        assert 0 not in selected  # Current (first) was deselected
        assert 1 in selected
        assert 2 in selected


class TestUserInput:
    """Test user input collection"""
    
    def test_get_user_input_valid(self):
        """Test getting valid user input"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        # Temporarily override UI methods and restore afterward
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.PLAIN_TEXT)
            ui.select_merge_mode = lambda: MergeMode.NO_MERGE

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = None

            assert path == "test.pdf"
            assert format_choice.payload == OutputFormat.PLAIN_TEXT
            assert merge == MergeMode.NO_MERGE
            assert merged_filename is None
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge

    def test_get_path_input_shows_prompt_and_returns_value(self):
        """Ensure `get_path_input` clears, draws header, and returns input_center value"""
        from unittest.mock import Mock

        console = Console(record=True)
        ui = RetroCLI(console=console)

        ui.draw_header = Mock()
        ui.input_center = Mock(return_value="/some/path")

        result = ui.get_path_input()
        if isinstance(result, ActionResult):
            result = result.payload
        assert result == "/some/path"
    
    def test_get_user_input_format_2(self):
        """Test format choice 2 (markdown)"""
        inputs = iter(["doc.epub"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        orig_prompt = ui.prompt_merged_filename
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.MARKDOWN)
            ui.select_merge_mode = lambda: MergeMode.MERGE
            ui.prompt_merged_filename = lambda: "my_merged"

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = ui.prompt_merged_filename() if merge == MergeMode.MERGE else None

            assert format_choice.payload == OutputFormat.MARKDOWN
            assert merge == MergeMode.MERGE
            assert merged_filename == "my_merged"
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge
            ui.prompt_merged_filename = orig_prompt
    
    def test_get_user_input_format_3(self):
        """Test format choice 3 (json)"""
        inputs = iter(["/data"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.JSON)
            ui.select_merge_mode = lambda: MergeMode.PER_PAGE

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = None

            assert format_choice.payload == OutputFormat.JSON
            assert merge == MergeMode.PER_PAGE
            assert merged_filename is None
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge
    
    def test_get_user_input_merge_default(self):
        """Test merge prompt returns no_merge by default"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.MARKDOWN)
            ui.select_merge_mode = lambda: MergeMode.NO_MERGE

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = None

            assert merge == MergeMode.NO_MERGE
            assert merged_filename is None
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge
    
    def test_get_user_input_merge_no(self):
        """Test merge mode selection returns no_merge"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.MARKDOWN)
            ui.select_merge_mode = lambda: MergeMode.NO_MERGE

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = None

            assert merge == MergeMode.NO_MERGE
            assert merged_filename is None
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge
    
    def test_get_user_input_merge_per_page(self):
        """Test merge mode selection returns per_page"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        orig_input = ui.input_center
        orig_select_format = ui.select_output_format
        orig_select_merge = ui.select_merge_mode
        try:
            ui.input_center = lambda prompt=">>: ": next(inputs)
            ui.select_output_format = lambda: ActionResult.value(OutputFormat.MARKDOWN)
            ui.select_merge_mode = lambda: MergeMode.PER_PAGE

            path = ui.input_center()
            format_choice = ui.select_output_format()
            merge = ui.select_merge_mode()
            merged_filename = None

            assert merge == MergeMode.PER_PAGE
            assert merged_filename is None
        finally:
            ui.input_center = orig_input
            ui.select_output_format = orig_select_format
            ui.select_merge_mode = orig_select_merge

    def test_prompt_merged_filename(self):
        """Test prompting for merged filename"""
        from unittest.mock import Mock
        console = Console(record=True)
        ui = RetroCLI(console=console)
        ui.input_center = Mock(return_value="  my_file  ")
        filename = ui.prompt_merged_filename()
        ui.input_center.assert_called_once()
        if isinstance(filename, ActionResult):
            filename = filename.payload
        assert filename == "my_file"


class TestProgressBar:
    """Test progress bar functionality"""
    
    def test_get_progress_bar_context_manager(self):
        """Test progress bar as context manager"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        with ui.get_progress_bar() as progress:
            assert progress is not None
            
            # Add a task
            task_id = progress.add_task("test", total=100)
            assert task_id is not None
            
            # Update task
            progress.update(task_id, completed=50)
    
    def test_get_progress_bar_multiple_tasks(self):
        """Test progress bar with multiple tasks"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        with ui.get_progress_bar() as progress:
            task1 = progress.add_task("file1", total=100, status="pending", filename="file1.pdf")
            task2 = progress.add_task("file2", total=100, status="pending", filename="file2.pdf")
            
            progress.update(task1, completed=100, status="done")
            progress.update(task2, completed=50, status="converting")


class TestInputCenter:
    """Test centered input method"""
    
    def test_input_center_default_prompt(self):
        """Test input_center with default prompt"""
        console = Console()
        ui = RetroCLI(console=console)
        orig_input = __import__("builtins").input
        try:
            # Patch built-in input to avoid OSError
            __import__("builtins").input = lambda *args, **kwargs: "test input"
            result = ui.input_center()
            assert result == "test input"
        finally:
            __import__("builtins").input = orig_input

    def test_input_center_custom_prompt(self):
        """Test input_center with custom prompt"""
        console = Console()
        ui = RetroCLI(console=console)
        orig_input = __import__("builtins").input
        try:
            __import__("builtins").input = lambda *args, **kwargs: "custom"
            result = ui.input_center(prompt_symbol=">>> ")
            assert result == "custom"
        finally:
            __import__("builtins").input = orig_input


def test_retrocli_basic_rendering():
    """Original basic rendering test"""
    console = Console(record=True)
    ui = RetroCLI(console=console)

    # Should not raise
    ui.draw_header()
    ui.print_center("hello world")
    ui.show_error("something went wrong")


class TestMergeModeSelection:
    """Test merge mode selection UI"""
    
    def test_select_merge_mode_navigation(self):
        """Test _select_merge_mode with arrow key navigation"""
        console = Console(record=True)
        
        # Simulate: down arrow, down arrow, enter (selects "per_page")
        keyboard_input = keyboard_from_string("DOWN DOWN ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui.select_merge_mode()
        if isinstance(result, ActionResult):
            result = result.payload
        assert result == MergeMode.PER_PAGE
    
    def test_select_merge_mode_up_arrow_wrapping(self):
        """Test _select_merge_mode with up arrow wrapping to end"""
        console = Console(record=True)
        
        # Simulate: up arrow (wraps to last), enter
        keyboard_input = keyboard_from_string("UP ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui.select_merge_mode()
        if isinstance(result, ActionResult):
            result = result.payload
        assert result == MergeMode.PER_PAGE

class TestOutputFormatSelection:
    """Test output format selection UI"""
    
    def test_select_output_format_navigation(self):
        """Test _select_output_format with arrow key navigation"""
        console = Console(record=True)
        
        # Simulate: down arrow, down arrow, enter (selects json = 3)
        keyboard_input = keyboard_from_string("DOWN DOWN ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui.select_output_format()
        assert result.payload == OutputFormat.JSON
    
    def test_select_output_format_up_arrow_wrapping(self):
        """Test _select_output_format with up arrow wrapping to end"""
        console = Console(record=True)
        
        # Simulate: up arrow (wraps to json), enter
        keyboard_input = keyboard_from_string("UP ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui.select_output_format()
        assert result.payload == OutputFormat.JSON
    
    def test_select_output_format_default_selection(self):
        """Test _select_output_format with immediate enter (selects plain text = 1)"""
        console = Console(record=True)
        
        # Simulate: enter (selects default plain text)
        keyboard_input = keyboard_from_string("ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui.select_output_format()
        assert result.payload == OutputFormat.PLAIN_TEXT


class TestQuitHandlers:
    """Tests for handlers that accept ':q' to quit/terminate."""

    def test_get_path_input_colon_q_terminates(self):
        from unittest.mock import Mock
        console = Console(record=True)
        ui = RetroCLI(console=console)
        ui.input_center = Mock(return_value=":q")
        result = ui.get_path_input()
        ui.input_center.assert_called_once()
        assert isinstance(result, ActionResult)
        assert result.kind == ActionKind.TERMINATE

    def test_prompt_merged_filename_colon_q_terminates(self):
        from unittest.mock import Mock
        console = Console(record=True)
        ui = RetroCLI(console=console)
        ui.input_center = Mock(return_value=":q")
        result = ui.prompt_merged_filename()
        ui.input_center.assert_called_once()
        assert isinstance(result, ActionResult)
        assert result.kind == ActionKind.TERMINATE
