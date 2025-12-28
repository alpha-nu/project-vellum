import pytest
import time
from collections import defaultdict
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, patch

from rich.console import Console
from rich.text import Text

from view.ui import (
    RetroCLI,
    StyledTimeElapsedColumn,
    StyledPercentageColumn,
    StyledDescriptionColumn,
    _StyledTimeMixin,
)
from view.ui import MergeMode, OutputFormat
from view.keyboard import KeyboardToken, KeyboardKey

from domain.model.file import File


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
    
    def test_print_panel(self):
        """Test panel printing with different colors"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.print_panel("test message", content_color_key="primary")
        ui.print_panel("error message", content_color_key="error")
        
        text = console.export_text()
        assert "test message" in text
        assert "error message" in text


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
        assert "v.1.0.0" in text
    
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
        # Keybinding hint should be present for running again or quitting
        assert "run another conversion" in text
        assert "quit" in text
        
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
        assert "converter" in text.lower()
        assert "v.1.0.0" in text

    def test_ask_again_enter_and_quit(self):
        """ask_again should return True for Enter and False for 'q'"""
        console = Console(record=True)
        
        # Test Enter -> True
        keyboard_reader = keyboard_from_string("ENTER")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        assert ui.ask_again() is True

        # Test 'q' -> False
        keyboard_reader = keyboard_from_string("q")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        assert ui.ask_again() is False

    def test_ask_again_ignores_other_keys(self):
        """ask_again should ignore unrelated keys until a valid one is pressed"""
        console = Console(record=True)
        
        # Sequence: x (ignored), ENTER (accepted)
        keyboard_reader = keyboard_from_string("x ENTER")
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        assert ui.ask_again() is True



class TestInteractiveSelection:
    """Test interactive file selection"""
    
    @staticmethod
    def _paths_to_file_data(paths):
        """Convert Path objects to file data dicts for view."""
        return [File.from_path(p).to_dict() for p in paths]
    
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
        
        assert selected == []
    
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
        selected = ui.select_files(file_data)
        
        assert len(selected) == 1
        assert selected[0] == 0  # First file index
    
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
        
        assert len(selected) == 3
        assert selected == [0, 1, 2]  # All indices
    
    @patch('view.keyboard.readchar.readchar')
    def test_select_files_quit(self, mock_readchar, tmp_path):
        """Test quitting with 'q' key exits application"""
        files = [tmp_path / "file.pdf"]
        files[0].touch()
        
        # Simulate: 'q' (quit)
        mock_readchar.return_value = "q"
        keyboard_reader = keyboard_from_string("q")
        
        console = Console(record=True)
        ui = RetroCLI(console=console, keyboard_reader=keyboard_reader)
        
        file_data = self._paths_to_file_data(files)
        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            ui.select_files(file_data)
        
        assert exc_info.value.code == 0
    
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
        
        # Should have 2 files (all 3 selected, then current deselected)
        assert len(selected) == 2
        assert 0 not in selected  # Current (first) was deselected
        assert 1 in selected
        assert 2 in selected


class TestUserInput:
    """Test user input collection"""
    
    def test_get_user_input_valid(self, monkeypatch):
        """Test getting valid user input"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.PLAIN_TEXT)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.NO_MERGE)
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert path == "test.pdf"
        assert format_choice == OutputFormat.PLAIN_TEXT
        assert merge == MergeMode.NO_MERGE
        assert merged_filename is None
    
    def test_get_user_input_format_2(self, monkeypatch):
        """Test format choice 2 (markdown)"""
        inputs = iter(["doc.epub"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.MARKDOWN)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.MERGE)
        monkeypatch.setattr(ui, "_prompt_merged_filename", lambda: "my_merged")
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert format_choice == OutputFormat.MARKDOWN
        assert merge == MergeMode.MERGE
        assert merged_filename == "my_merged"
    
    def test_get_user_input_format_3(self, monkeypatch):
        """Test format choice 3 (json)"""
        inputs = iter(["/data"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.JSON)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.PER_PAGE)
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert format_choice == OutputFormat.JSON
        assert merge == MergeMode.PER_PAGE
        assert merged_filename is None
    
    def test_get_user_input_merge_default(self, monkeypatch):
        """Test merge prompt returns no_merge by default"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.MARKDOWN)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.NO_MERGE)
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert merge == MergeMode.NO_MERGE
        assert merged_filename is None
    
    def test_get_user_input_merge_no(self, monkeypatch):
        """Test merge mode selection returns no_merge"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.MARKDOWN)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.NO_MERGE)
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert merge == MergeMode.NO_MERGE
        assert merged_filename is None
    
    def test_get_user_input_merge_per_page(self, monkeypatch):
        """Test merge mode selection returns per_page"""
        inputs = iter(["test.pdf"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_output_format", lambda: OutputFormat.MARKDOWN)
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: MergeMode.PER_PAGE)
        
        path, format_choice, merge, merged_filename = ui.get_user_input()
        
        assert merge == MergeMode.PER_PAGE
        assert merged_filename is None

    def test_prompt_merged_filename(self, monkeypatch):
        """Test prompting for merged filename"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": "  my_file  ")
        
        filename = ui._prompt_merged_filename()
        
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
    
    def test_input_center_default_prompt(self, monkeypatch):
        """Test input_center with default prompt"""
        console = Console()
        ui = RetroCLI(console=console)
        
        # Mock console.input
        monkeypatch.setattr(console, "input", lambda *args, **kwargs: "test input")
        
        result = ui.input_center()
        
        assert result == "test input"
    
    def test_input_center_custom_prompt(self, monkeypatch):
        """Test input_center with custom prompt"""
        console = Console()
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(console, "input", lambda *args, **kwargs: "custom")
        
        result = ui.input_center(prompt_symbol=">>> ")
        
        assert result == "custom"


def test_retrocli_basic_rendering():
    """Original basic rendering test"""
    console = Console(record=True)
    ui = RetroCLI(console=console)

    # Should not raise
    ui.draw_header()
    ui.print_panel("hello world")
    ui.show_error("something went wrong")


class TestMergeModeSelection:
    """Test merge mode selection UI"""
    
    def test_select_merge_mode_navigation(self):
        """Test _select_merge_mode with arrow key navigation"""
        console = Console(record=True)
        
        # Simulate: down arrow, down arrow, enter (selects "per_page")
        keyboard_input = keyboard_from_string("DOWN DOWN ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui._select_merge_mode()
        assert result == MergeMode.PER_PAGE
    
    def test_select_merge_mode_up_arrow_wrapping(self):
        """Test _select_merge_mode with up arrow wrapping to end"""
        console = Console(record=True)
        
        # Simulate: up arrow (wraps to last), enter
        keyboard_input = keyboard_from_string("UP ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui._select_merge_mode()
        assert result == MergeMode.PER_PAGE

class TestOutputFormatSelection:
    """Test output format selection UI"""
    
    def test_select_output_format_navigation(self):
        """Test _select_output_format with arrow key navigation"""
        console = Console(record=True)
        
        # Simulate: down arrow, down arrow, enter (selects json = 3)
        keyboard_input = keyboard_from_string("DOWN DOWN ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui._select_output_format()
        assert result == OutputFormat.JSON
    
    def test_select_output_format_up_arrow_wrapping(self):
        """Test _select_output_format with up arrow wrapping to end"""
        console = Console(record=True)
        
        # Simulate: up arrow (wraps to json), enter
        keyboard_input = keyboard_from_string("UP ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui._select_output_format()
        assert result == OutputFormat.JSON
    
    def test_select_output_format_default_selection(self):
        """Test _select_output_format with immediate enter (selects plain text = 1)"""
        console = Console(record=True)
        
        # Simulate: enter (selects default plain text)
        keyboard_input = keyboard_from_string("ENTER")
        
        ui = RetroCLI(console=console, keyboard_reader=keyboard_input)
        
        result = ui._select_output_format()
        assert result == OutputFormat.PLAIN_TEXT