"""Controller unit tests with full mock isolation."""

import pytest
from pytest import raises
from unittest.mock import patch
from controller.converter_controller import ConverterController, NextAction
from tests.controller.conftest import MockUIBuilder, MockConverter, MockHandler, MockPathBuilder
from view.ui import MergeMode, OutputFormat


class TestGetConverter:
    """Tests for _get_converter method."""
    
    def test_returns_converter_for_supported_extension(self):
        ui = MockUIBuilder().build()
        pdf_converter = MockConverter
        controller = ConverterController(ui, {".pdf": pdf_converter}, {}, lambda s: None)
        
        mock_path = MockPathBuilder().with_suffix(".pdf").build()
        converter = controller._get_converter(mock_path)
        
        assert converter.__class__.__name__ == "MockConverter"
    
    def test_returns_none_for_unsupported_extension(self):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {".pdf": MockConverter}, {}, lambda s: None)
        
        mock_path = MockPathBuilder().with_suffix(".docx").build()
        converter = controller._get_converter(mock_path)
        
        assert converter is None


class TestGetCompatibleFiles:
    """Tests for _get_compatible_files method."""
    
    def test_filters_by_supported_extensions(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        
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
    
    def test_returns_handler_for_valid_format(self):
        ui = MockUIBuilder().build()
        text_handler = MockHandler
        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: text_handler}, lambda s: None)
        
        handler = controller._get_format_handler(OutputFormat.PLAIN_TEXT)
        
        assert handler.__class__.__name__ == "MockHandler"
    
    def test_raises_for_unknown_format(self):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {}, {}, lambda s: None)
        
        with raises(ValueError, match="Unknown output format"):
            controller._get_format_handler(OutputFormat.PLAIN_TEXT)


class TestRun:
    """Tests for run method."""
    
    def test_loops_while_restart(self, mock_converters, mock_handlers):
        """Test run continues while _run_once returns RESTART."""
        ui = MockUIBuilder("test.pdf").with_run_again(True).build()
        
        path_factory = MockPathBuilder().with_suffix(".pdf").with_stem("test").build_factory()
        controller = ConverterController(ui, mock_converters, mock_handlers, path_factory)
        
        controller.run()
        
        assert ui.ask_again.call_count == 2


class TestRunOnce:
    """Tests for _run_once method."""
    
    def test_path_not_found_shows_error_and_quits(self, mock_converters, mock_handlers):
        ui = MockUIBuilder("nonexistent.pdf").build()
        
        path_factory = MockPathBuilder().with_exists(False).build_factory()
        controller = ConverterController(ui, mock_converters, mock_handlers, path_factory)
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT
        ui.show_error.assert_called_once()
        assert "path not found" in ui.show_error.call_args[0][0]
    
    def test_no_compatible_files_shows_error_and_quits(self, mock_converters, mock_handlers):
        ui = MockUIBuilder("/some/dir").build()
        
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
        controller = ConverterController(ui, mock_converters, mock_handlers, path_factory)
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT
        ui.show_error.assert_called_once()
        assert "no compatible files found" in ui.show_error.call_args[0][0]
    
    def test_successful_single_file_conversion(self, mock_converters, mock_handlers, mock_pdf_path):
        ui = MockUIBuilder("test.pdf").build()
        
        controller = ConverterController(ui, mock_converters, mock_handlers, mock_pdf_path)
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT
        ui.show_conversion_summary.assert_called_once()
        assert ui.show_conversion_summary.call_args.kwargs['total_files'] == 1
    
    def test_ask_again_true_returns_restart(self, mock_converters, mock_handlers, mock_pdf_path):
        ui = MockUIBuilder("test.pdf").with_run_again(True).build()
        
        controller = ConverterController(ui, mock_converters, mock_handlers, mock_pdf_path)
        
        result = controller._run_once()
        
        assert result == NextAction.RESTART
    
    def test_ask_again_exception_returns_quit(self, mock_converters, mock_handlers, mock_pdf_path):
        """Test that exception in ask_again results in QUIT."""
        ui = MockUIBuilder("test.pdf").build()
        
        # Override ask_again to raise exception
        def raise_exception():
            raise NotImplementedError()
        ui.ask_again = raise_exception
        
        controller = ConverterController(ui, mock_converters, mock_handlers, mock_pdf_path)
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT


class TestGetFilesToProcess:
    """Tests for _get_files_to_process method."""
    
    def test_single_file_returns_list_with_file(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        
        mock_path = MockPathBuilder().with_is_dir(False).with_suffix(".pdf").build()
        
        files = controller._get_files_to_process(mock_path)
        
        assert files == [mock_path]

class TestProcessFiles:
    """Tests for _process_files method."""
    
    def test_no_merge_mode_saves_individual_files(self, mock_converters, mock_handlers, mock_pdf_path):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        accumulator, output_count, total_size = controller._process_files(
            [mock_pdf_path(None)], handler, MergeMode.NO_MERGE
        )
        
        assert accumulator == []
        assert output_count == 1
        assert total_size > 0
    
    def test_merge_mode_accumulates_content(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        files = [
            MockPathBuilder().with_suffix(".pdf").with_stem("doc1").build(),
            MockPathBuilder().with_suffix(".pdf").with_stem("doc2").build(),
        ]
        
        accumulator, output_count, total_size = controller._process_files(
            files, handler, MergeMode.MERGE
        )
        
        assert len(accumulator) == 2
        assert "doc1.pdf" in accumulator[0]
        assert "doc2.pdf" in accumulator[1]
        assert output_count == 0
    
    def test_per_page_mode_saves_multiple(self, mock_converters, mock_handlers, mock_pdf_path):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, mock_pdf_path)
        handler = MockHandler()
        
        accumulator, output_count, total_size = controller._process_files(
            [mock_pdf_path(None)], handler, MergeMode.PER_PAGE
        )
        
        assert accumulator == []
        assert output_count == 3  # MockConverter returns 3 pages


class TestProcessSingleFile:
    """Tests for _process_single_file method."""
    
    def test_unsupported_file_returns_zeros(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        # Create a mock progress tracker
        class MockProgress:
            def update(self, *a, **kw): pass
        
        # Unsupported extension
        mock_file = MockPathBuilder().with_suffix(".docx").with_stem("test").build()
        
        content, count, size = controller._process_single_file(
            mock_file, 1, MockProgress(), handler, MergeMode.NO_MERGE
        )
        
        assert content is None
        assert count == 0
        assert size == 0
    
    def test_progress_callback_exception_handled(self, mock_converters, mock_handlers, mock_pdf_path):
        """Test that exceptions in progress callback don't crash processing."""
        ui = MockUIBuilder().with_progress_exception_on_update(2).build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        # Should not raise despite progress exception
        with ui.get_progress_bar() as progress:
            task_id = progress.add_task("", total=100)
            content, count, size = controller._process_single_file(
                mock_pdf_path(None), task_id, progress, handler, MergeMode.NO_MERGE
            )
        
        assert content is not None


class TestSaveMergedOutput:
    """Tests for _save_merged_output method."""
    
    def test_with_custom_filename_in_directory(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        mock_dir = MockPathBuilder("/output").with_is_dir(True).build()
        accumulator = ["content1", "content2"]
        
        filename, size = controller._save_merged_output(
            mock_dir, handler, accumulator, OutputFormat.PLAIN_TEXT, "custom_name"
        )
        
        assert "custom_name" in filename
        assert ".txt" in filename
    
    def test_with_custom_filename_for_file(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        mock_file = MockPathBuilder("/path/input.pdf").with_is_dir(False).build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_file, handler, accumulator, OutputFormat.MARKDOWN, "my_merged"
        )
        
        assert "my_merged" in filename
        assert ".md" in filename
    
    def test_default_filename_for_directory(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        mock_dir = MockPathBuilder("/output").with_is_dir(True).build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_dir, handler, accumulator, OutputFormat.JSON, None
        )
        
        assert "merged_output" in filename
        assert ".json" in filename
    
    def test_default_filename_for_file(self, mock_converters, mock_handlers):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, mock_converters, mock_handlers, lambda s: None)
        handler = MockHandler()
        
        mock_file = MockPathBuilder().with_is_dir(False).with_stem("source").build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_file, handler, accumulator, OutputFormat.PLAIN_TEXT, None
        )
        
        assert "source_merged" in filename


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""
    
    def test_merge_mode_saves_merged_output_and_adds_size(self, mock_converters, mock_handlers):
        """Test that merge mode calls _save_merged_output and adds merge_output_size to total."""
        mock_file = MockPathBuilder().with_suffix(".pdf").with_stem("doc").build()
        
        ui = (
            MockUIBuilder("doc.pdf")
            .with_merge_mode(MergeMode.MERGE)
            .with_merged_filename("merged")
            .build()
        )
        
        controller = ConverterController(
            ui, mock_converters, mock_handlers, lambda s: mock_file
        )
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT
        ui.show_conversion_summary.assert_called_once()
        call_kwargs = ui.show_conversion_summary.call_args.kwargs
        assert call_kwargs['output_count'] == 1
        assert "merged" in call_kwargs['merged_filename']
    

    def test_per_page_mode_full_flow(self, mock_converters, mock_handlers):
        """Test per-page output mode."""
        mock_file = MockPathBuilder().with_suffix(".pdf").with_stem("multipage").build()
        
        ui = MockUIBuilder("multipage.pdf").with_merge_mode(MergeMode.PER_PAGE).build()
        
        controller = ConverterController(
            ui, mock_converters, mock_handlers, lambda s: mock_file
        )
        
        result = controller._run_once()
        
        assert result == NextAction.QUIT
        ui.show_conversion_summary.assert_called_once()
        assert ui.show_conversion_summary.call_args.kwargs['output_count'] == 3  # MockConverter returns 3 pages


