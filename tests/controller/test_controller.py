"""Controller unit tests with full mock isolation."""

import pytest
from pytest import raises
from unittest.mock import patch, MagicMock
from controller.converter_controller import ConverterController, NextAction
from tests.controller.conftest import MockUIBuilder, MockPathBuilder
from view.merge_mode import MergeMode
from view.output_format import OutputFormat


class TestGetConverter:
    """Tests for _get_converter method."""
    
    def test_returns_converter_for_supported_extension(self, mock_converter):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {".pdf": mock_converter}, {}, lambda s: None)
        
        mock_path = MockPathBuilder().with_suffix(".pdf").build()
        converter = controller._get_converter(mock_path)
        
        assert converter is not None
        assert hasattr(converter, 'extract_content')
    
    def test_returns_none_for_unsupported_extension(self, mock_converter):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {".pdf": mock_converter}, {}, lambda s: None)
        
        mock_path = MockPathBuilder().with_suffix(".docx").build()
        converter = controller._get_converter(mock_path)
        
        assert converter is None


class TestGetCompatibleFiles:
    """Tests for _get_compatible_files method."""
    
    def test_filters_by_supported_extensions(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_path = (
            MockPathBuilder("/mock_dir")
            .with_is_dir(True)
            .with_files([
                MockPathBuilder().with_suffix(".pdf").with_stem("file1").build(),
                MockPathBuilder().with_suffix(".epub").with_stem("file2").build(),
                MockPathBuilder().with_suffix(".txt").with_stem("file3").build(),
            ])
            .build()
        )
        
        compatible = controller._get_compatible_files(mock_path)
        
        assert {f.name for f in compatible} == {"file1.pdf", "file2.epub"}


class TestGetFormatHandler:
    """Tests for _get_format_handler method."""
    
    def test_returns_handler_for_valid_format(self, mock_handler):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: mock_handler}, lambda s: None)
        
        handler = controller._get_format_handler(OutputFormat.PLAIN_TEXT)
        
        assert handler is not None
        assert hasattr(handler, 'save')
    
    def test_raises_for_unknown_format(self):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {}, {}, lambda s: None)
        
        with raises(ValueError, match="Unknown output format"):
            controller._get_format_handler(OutputFormat.PLAIN_TEXT)


class TestRun:
    """Tests for run method."""
    
    def test_loops_while_restart(self, mock_converters, mock_handler):
        """Test run continues while _run_once returns RESTART."""
        ui = MockUIBuilder("test.pdf").with_run_again(True).build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        path_factory = MockPathBuilder().with_suffix(".pdf").with_stem("test").build_factory()
        controller = ConverterController(ui, mock_converters, handlers, path_factory)
        
        controller.run()
        
        assert ui.ask_again.call_count == 2


class TestRunOnce:
    """Tests for _run_once method."""
    
    def test_path_not_found_shows_error_and_quits(self, mock_converters, mock_handler):
        ui = MockUIBuilder("nonexistent.pdf").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        path_factory = MockPathBuilder().with_exists(False).build_factory()
        controller = ConverterController(ui, mock_converters, handlers, path_factory)
        
        # Run one step and assert error shown
        controller.run(loop=False)
        ui.show_error.assert_called_once()
        assert "path not found" in ui.show_error.call_args[0][0]
    
    def test_no_compatible_files_shows_error_and_quits(self, mock_converters, mock_handler):
        ui = MockUIBuilder("/some/dir").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        # Directory with no compatible files
        mock_path = (
            MockPathBuilder("/some/dir")
            .with_exists(True)
            .with_is_dir(True)
            .with_files([
                MockPathBuilder().with_suffix(".txt").with_stem("readme").build(),
            ])
            .build()
        )
        path_factory = lambda s: mock_path
        controller = ConverterController(ui, mock_converters, handlers, path_factory)
        
        # Drive controller through source -> format -> merge -> files selection
        controller.run(loop=False)  # SOURCE_INPUT
        controller.run(loop=False)  # FORMAT_SELECTION
        controller.run(loop=False)  # MERGE_MODE_SELECTION
        controller.run(loop=False)  # FILES_SELECTION -> should trigger error
        ui.show_error.assert_called_once()
        assert "no compatible files found" in ui.show_error.call_args[0][0]
    
    def test_successful_single_file_conversion(self, mock_converters, mock_handler, mock_pdf_path):
        ui = MockUIBuilder("test.pdf").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        controller = ConverterController(ui, mock_converters, handlers, mock_pdf_path)
        
        # Drive the controller until processing summary is shown
        while not ui.show_conversion_summary.called:
            controller.run(loop=False)

        # Advance once to COMPLETE and handle ask_again
        result = controller.run(loop=False)

        assert ui.show_conversion_summary.call_count == 1
        assert ui.show_conversion_summary.call_args.kwargs['total_files'] == 1
        assert result is False
    
    def test_ask_again_true_returns_restart(self, mock_converters, mock_handler, mock_pdf_path):
        ui = MockUIBuilder("test.pdf").with_run_again(True).build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        controller = ConverterController(ui, mock_converters, handlers, mock_pdf_path)
        
        # Drive until summary, then handle COMPLETE which should restart
        while not ui.show_conversion_summary.called:
            controller.run(loop=False)

        result = controller.run(loop=False)

        assert result is True
    
    def test_ask_again_exception_returns_quit(self, mock_converters, mock_handler, mock_pdf_path):
        """Test that exception in ask_again results in QUIT."""
        ui = MockUIBuilder("test.pdf").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        # Override ask_again to raise exception
        def raise_exception():
            raise NotImplementedError()
        ui.ask_again = raise_exception
        
        controller = ConverterController(ui, mock_converters, handlers, mock_pdf_path)
        
        # Drive until summary and then handle COMPLETE which should quit on exception
        while not ui.show_conversion_summary.called:
            controller.run(loop=False)

        result = controller.run(loop=False)

        assert result is False


class TestGetFilesToProcess:
    """Tests for _get_files_to_process method."""
    
    def test_single_file_returns_list_with_file(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_path = MockPathBuilder().with_is_dir(False).with_suffix(".pdf").build()
        
        files = controller._get_files_to_process(mock_path)
        
        assert files == [mock_path]


class TestProcessFiles:
    """Tests for _process_files method."""
    
    def test_no_merge_mode_saves_individual_files(self, mock_converters, mock_handler, mock_pdf_path):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        accumulator, output_count, total_size = controller._process_files(
            [mock_pdf_path(None)], mock_handler, MergeMode.NO_MERGE
        )
        
        assert accumulator == []
        assert output_count == 1
        assert total_size > 0
    
    def test_merge_mode_accumulates_content(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        files = [
            MockPathBuilder().with_suffix(".pdf").with_stem("doc1").build(),
            MockPathBuilder().with_suffix(".pdf").with_stem("doc2").build(),
        ]
        
        accumulator, output_count, total_size = controller._process_files(
            files, mock_handler, MergeMode.MERGE
        )
        
        assert len(accumulator) == 2
        assert "doc1.pdf" in accumulator[0]
        assert "doc2.pdf" in accumulator[1]
        assert output_count == 0
    
    def test_per_page_mode_saves_multiple(self, mock_converters, mock_handler, mock_pdf_path):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, mock_pdf_path)
        
        accumulator, output_count, total_size = controller._process_files(
            [mock_pdf_path(None)], mock_handler, MergeMode.PER_PAGE
        )
        
        assert accumulator == []
        assert output_count == 3  # MockConverter returns 3 pages


class TestProcessSingleFile:
    """Tests for _process_single_file method."""
    
    def test_unsupported_file_returns_zeros(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        # Create a mock progress tracker
        class MockProgress:
            def update(self, *a, **kw): pass
        
        # Unsupported extension
        mock_file = MockPathBuilder().with_suffix(".docx").with_stem("test").build()
        
        content, count, size = controller._process_single_file(
            mock_file, 1, MockProgress(), mock_handler, MergeMode.NO_MERGE
        )
        
        assert content is None
        assert count == 0
        assert size == 0
    
    def test_processes_supported_file_successfully(self, mock_converters, mock_handler, mock_pdf_path):
        """Test that a supported file is processed and returns content."""
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        with ui.get_progress_bar() as progress:
            task_id = progress.add_task("", total=100)
            content, count, size = controller._process_single_file(
                mock_pdf_path(None), task_id, progress, mock_handler, MergeMode.NO_MERGE
            )
        
        assert content is not None
    
    def test_progress_callback_exception_is_silently_handled(self, mock_handler):
        """Test that exceptions in progress callback are caught and don't crash processing."""
        # Create a converter that actually invokes the progress callback
        def converter_that_calls_callback(path, *args, **kwargs):
            mock = MagicMock()
            mock.path = path
            def extract_with_callback(progress_callback=None):
                if progress_callback:
                    progress_callback(1, 2)  # This will trigger the exception inside the callback
                return "content"
            mock.extract_content = MagicMock(side_effect=extract_with_callback)
            mock.extract_content_per_item = MagicMock(return_value=["page1"])
            return mock
        
        converters = {".pdf": converter_that_calls_callback}
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        # Create a progress bar that raises only on the 2nd call (inside progress_callback)
        # Call 1: initial progress update (line 308) - OK
        # Call 2: from progress_callback (line 323-332) - should FAIL but be caught
        # Call 3: final progress update (line 358) - OK
        class ExplodingProgressOnCallback:
            def __init__(self):
                self.call_count = 0
            
            def update(self, *args, **kwargs):
                self.call_count += 1
                if self.call_count == 2:  # Only explode on the callback call (2nd call)
                    raise RuntimeError("Progress update failed!")
        
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, converters, handlers, lambda s: None)
        
        mock_file = MockPathBuilder().with_suffix(".pdf").with_stem("test").build()
        
        # Should NOT raise - the exception in the callback should be silently caught
        content, count, size = controller._process_single_file(
            mock_file, 1, ExplodingProgressOnCallback(), mock_handler, MergeMode.NO_MERGE
        )
        
        assert content == "content"


class TestSaveMergedOutput:
    """Tests for _save_merged_output method."""
    
    def test_with_custom_filename_in_directory(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_dir = MockPathBuilder("/output").with_is_dir(True).build()
        accumulator = ["content1", "content2"]
        
        filename, size = controller._save_merged_output(
            mock_dir, mock_handler, accumulator, OutputFormat.PLAIN_TEXT, "custom_name"
        )
        
        assert "custom_name" in filename
        assert ".txt" in filename
    
    def test_with_custom_filename_for_file(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_file = MockPathBuilder("/path/input.pdf").with_is_dir(False).build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_file, mock_handler, accumulator, OutputFormat.MARKDOWN, "my_merged"
        )
        
        assert "my_merged" in filename
        assert ".md" in filename
    
    def test_default_filename_for_directory(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_dir = MockPathBuilder("/output").with_is_dir(True).build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_dir, mock_handler, accumulator, OutputFormat.JSON, None
        )
        
        assert "merged_output" in filename
        assert ".json" in filename
    
    def test_default_filename_for_file(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_file = MockPathBuilder().with_is_dir(False).with_stem("source").build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_file, mock_handler, accumulator, OutputFormat.PLAIN_TEXT, None
        )
        
        assert "source_merged" in filename


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""
    
    def test_merge_mode_saves_merged_output_and_adds_size(self, mock_converters, mock_handler):
        """Test that merge mode calls _save_merged_output and adds merge_output_size to total."""
        mock_file = MockPathBuilder().with_suffix(".pdf").with_stem("doc").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        ui = (
            MockUIBuilder("doc.pdf")
            .with_merge_mode(MergeMode.MERGE)
            .with_merged_filename("merged")
            .build()
        )
        
        controller = ConverterController(
            ui, mock_converters, handlers, lambda s: mock_file
        )
        
        # Drive until summary shown
        while not ui.show_conversion_summary.called:
            controller.run(loop=False)

        # Advance to COMPLETE and handle ask_again
        result = controller.run(loop=False)

        assert ui.show_conversion_summary.call_count == 1
        call_kwargs = ui.show_conversion_summary.call_args.kwargs
        assert call_kwargs['output_count'] == 1
        assert "merged" in call_kwargs['merged_filename']
        assert result is False
    

    def test_per_page_mode_full_flow(self, mock_converters, mock_handler):
        """Test per-page output mode."""
        mock_file = MockPathBuilder().with_suffix(".pdf").with_stem("multipage").build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        
        ui = MockUIBuilder("multipage.pdf").with_merge_mode(MergeMode.PER_PAGE).build()
        
        controller = ConverterController(
            ui, mock_converters, handlers, lambda s: mock_file
        )
        
        # Drive until summary shown
        while not ui.show_conversion_summary.called:
            controller.run(loop=False)

        # Advance to COMPLETE and handle ask_again
        result = controller.run(loop=False)

        assert ui.show_conversion_summary.call_count == 1
        assert ui.show_conversion_summary.call_args.kwargs['output_count'] == 3  # MockConverter returns 3 pages
        assert result is False


