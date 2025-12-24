import pytest
from rich.console import Console
from rich.text import Text
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager

from view.ui import (
    RetroCLI,
    StyledTimeElapsedColumn,
    StyledPercentageColumn,
    StyledDescriptionColumn,
    _StyledTimeMixin,
)


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
        import time
        column = StyledTimeElapsedColumn("cyan")
        
        # Create mock task with start time
        task = Mock()
        start_time = time.perf_counter() - 5.0  # Started 5 seconds ago
        task.fields = {
            "status": "converting",
            "filename": "test.pdf",
            "start_time": start_time
        }
        
        result = column.render(task)
        # Should show elapsed time (approximately 5 seconds)
        assert "00:0" in str(result)
    
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
    
    def test_show_no_files(self):
        """Test no files message"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.show_no_files()
        
        text = console.export_text()
        assert "no compatible files" in text.lower()
    
    def test_show_merge_complete(self):
        """Test merge completion message"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.show_merge_complete("merged_output.txt")
        
        text = console.export_text()
        assert "merge complete" in text.lower()
        assert "merged_output.txt" in text
    
    def test_show_shutdown(self):
        """Test shutdown message with various times"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        ui.show_shutdown(1.23)
        
        text = console.export_text()
        assert "conversion complete" in text.lower()
        assert "1.23" in text
    
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


class TestInteractiveSelection:
    """Test interactive file selection"""
    
    @staticmethod
    def _paths_to_file_data(paths):
        """Convert Path objects to file data dicts for view."""
        from model.file import File
        return [File(p).to_dict() for p in paths]
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_enter_immediately(self, mock_readchar, tmp_path):
        """Test selecting files by pressing enter immediately (no selection)"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate pressing Enter immediately
        mock_readchar.return_value = "\r"
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        assert selected == []
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_space_then_enter(self, mock_readchar, tmp_path):
        """Test selecting file with space then enter"""
        files = [tmp_path / f"file{i}.pdf" for i in range(2)]
        for f in files:
            f.touch()
        
        # Simulate: space (select), enter (confirm)
        mock_readchar.side_effect = [" ", "\r"]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        assert len(selected) == 1
        assert selected[0] == 0  # First file index
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_down_arrow(self, mock_readchar, tmp_path):
        """Test navigating with down arrow"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: down arrow (escape sequence), space, enter
        mock_readchar.side_effect = [
            "\x1b", "[", "B",  # Down arrow
            " ",                # Space to select
            "\r"                # Enter
        ]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        # Should select second file (index 1)
        assert len(selected) == 1
        assert selected[0] == 1
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_up_arrow(self, mock_readchar, tmp_path):
        """Test navigating with up arrow"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: up arrow (wraps to last), space, enter
        mock_readchar.side_effect = [
            "\x1b", "[", "A",  # Up arrow (wraps around)
            " ",                # Space to select
            "\r"                # Enter
        ]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        # Should wrap to last file
        assert len(selected) == 1
        assert selected[0] == 2  # Last file index
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_toggle_on_off(self, mock_readchar, tmp_path):
        """Test toggling selection on and off"""
        files = [tmp_path / "file.pdf"]
        files[0].touch()
        
        # Simulate: space (select), space (deselect), enter
        mock_readchar.side_effect = [" ", " ", "\r"]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        # Should be deselected
        assert selected == []
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_select_all(self, mock_readchar, tmp_path):
        """Test selecting all with 'a' key - should select but not confirm"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), enter (confirm)
        mock_readchar.side_effect = ["a", "\r"]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        assert len(selected) == 3
        assert selected == [0, 1, 2]  # All indices
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_quit(self, mock_readchar, tmp_path):
        """Test quitting with 'q' key exits application"""
        files = [tmp_path / "file.pdf"]
        files[0].touch()
        
        # Simulate: 'q' (quit)
        mock_readchar.return_value = "q"
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        # Should raise SystemExit
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            ui.select_files(file_data)
        
        assert exc_info.value.code == 0
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_all_toggle_deselect(self, mock_readchar, tmp_path):
        """Test [A] pressed twice toggles: select all then deselect all"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), 'a' (deselect all), enter
        mock_readchar.side_effect = ["a", "a", "\r"]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        file_data = self._paths_to_file_data(files)
        selected = ui.select_files(file_data)
        
        # Should be empty after toggle
        assert len(selected) == 0
    
    @patch('view.ui.readchar.readchar')
    def test_select_files_all_continues_loop(self, mock_readchar, tmp_path):
        """Test [A] selects all but allows further navigation before confirm"""
        files = [tmp_path / f"file{i}.pdf" for i in range(3)]
        for f in files:
            f.touch()
        
        # Simulate: 'a' (select all), space (deselect current), enter
        mock_readchar.side_effect = ["a", " ", "\r"]
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
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
        inputs = iter(["test.pdf", "1"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "no_merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert path == "test.pdf"
        assert format_choice == 1
        assert merge == "no_merge"
    
    def test_get_user_input_format_2(self, monkeypatch):
        """Test format choice 2 (markdown)"""
        inputs = iter(["doc.epub", "2"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert format_choice == 2
        assert merge == "merge"
    
    def test_get_user_input_format_3(self, monkeypatch):
        """Test format choice 3 (json)"""
        inputs = iter(["/data", "3"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "per_page")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert format_choice == 3
        assert merge == "per_page"
    
    def test_get_user_input_invalid_format_retry(self, monkeypatch):
        """Test invalid format choice with retry"""
        inputs = iter(["test.pdf", "99", "1"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "no_merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert format_choice == 1
        
        # Check error message was shown
        text = console.export_text()
        assert "enter 1, 2, or 3" in text.lower()
    
    def test_get_user_input_empty_format(self, monkeypatch):
        """Test empty format input retries"""
        inputs = iter(["test.pdf", "", "2"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "no_merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert format_choice == 2
    
    def test_get_user_input_merge_default(self, monkeypatch):
        """Test merge prompt returns no_merge by default"""
        inputs = iter(["test.pdf", "1"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "no_merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert merge == "no_merge"
    
    def test_get_user_input_merge_no(self, monkeypatch):
        """Test merge mode selection returns no_merge"""
        inputs = iter(["test.pdf", "1"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "no_merge")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert merge == "no_merge"
    
    def test_get_user_input_merge_per_page(self, monkeypatch):
        """Test merge mode selection returns per_page"""
        inputs = iter(["test.pdf", "1"])
        
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        monkeypatch.setattr(ui, "input_center", lambda prompt=">>: ": next(inputs))
        monkeypatch.setattr(ui, "_select_merge_mode", lambda: "per_page")
        
        path, format_choice, merge = ui.get_user_input()
        
        assert merge == "per_page"


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
    ui.show_no_files()
    ui.show_merge_complete("out.txt")
    ui.show_shutdown(1.23)


class TestMergeModeSelection:
    """Test merge mode selection UI"""
    
    def test_select_merge_mode_navigation(self, monkeypatch):
        """Test _select_merge_mode with arrow key navigation"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        # Simulate: down arrow, down arrow, enter (selects "per_page")
        key_sequence = [
            "\x1b", "[", "B",  # Down arrow
            "\x1b", "[", "B",  # Down arrow
            "\r"               # Enter
        ]
        key_iter = iter(key_sequence)
        
        import readchar
        monkeypatch.setattr(readchar, "readchar", lambda: next(key_iter))
        
        result = ui._select_merge_mode()
        assert result == "per_page"
    
    def test_select_merge_mode_up_arrow_wrapping(self, monkeypatch):
        """Test _select_merge_mode with up arrow wrapping to end"""
        console = Console(record=True)
        ui = RetroCLI(console=console)
        
        # Simulate: up arrow (wraps to last), enter
        key_sequence = [
            "\x1b", "[", "A",  # Up arrow (wraps to per_page)
            "\r"               # Enter
        ]
        key_iter = iter(key_sequence)
        
        import readchar
        monkeypatch.setattr(readchar, "readchar", lambda: next(key_iter))
        
        result = ui._select_merge_mode()
        assert result == "per_page"
