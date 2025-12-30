"""Controller unit tests with full mock isolation."""

import pytest
from pytest import raises
from unittest.mock import patch, MagicMock
from controller.converter_controller import ConverterController
from tests.controller.conftest import MockUIBuilder, MockPathBuilder
from view.merge_mode import MergeMode
from view.output_format import OutputFormat
from controller.workflow.state_machine import WorkflowState
from unittest.mock import MagicMock
from view.interface import ActionResult, ActionKind


class TestGetConverter:
    """Tests for _get_converter method."""
    
    def test_returns_converter_for_supported_extension(self, mock_converter):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {".pdf": mock_converter}, {}, lambda s: None)

        mock_path = MockPathBuilder().with_suffix(".pdf").build()
        converter = controller.converters['.pdf'](mock_path)

        assert converter is not None
        assert hasattr(converter, 'extract_content')
    
    def test_returns_none_for_unsupported_extension(self, mock_converter):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {".pdf": mock_converter}, {}, lambda s: None)

        mock_path = MockPathBuilder().with_suffix(".docx").build()
        with pytest.raises(KeyError):
            _ = controller.converters[mock_path.suffix](mock_path)


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

        handler = controller.handlers[OutputFormat.PLAIN_TEXT]()

        assert handler is not None
        assert hasattr(handler, 'save')
    
    def test_raises_for_unknown_format(self):
        ui = MockUIBuilder().build()
        controller = ConverterController(ui, {}, {}, lambda s: None)

        with raises(KeyError):
            _ = controller.handlers[OutputFormat.PLAIN_TEXT]()


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
        
        # First step transitions to ERROR, second step handles/display the error
        controller.run(loop=False)
        result = controller.run(loop=False)

        ui.show_error.assert_called_once()
        assert "path not found" in ui.show_error.call_args[0][0]
        assert result is False
    
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

    def test_error_retry_restores_origin(self, mock_converters, mock_handler):
        """If an ERROR has an origin, retrying should return to that state."""
        ui = MockUIBuilder("/some/dir").with_run_again(True).build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}

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

        # With early compatibility validation, the ERROR will be raised at SOURCE_INPUT.
        # First run transitions to ERROR; handling it with ask_again -> True should
        # restore to SOURCE_INPUT.
        controller.run(loop=False)  # SOURCE_INPUT -> sets ERROR
        result = controller.run(loop=False)  # ERROR -> ask_again -> restore

        assert result is True
        assert controller.state_machine.get_state() == WorkflowState.SOURCE_INPUT

    def test_error_retry_with_no_origin_resets(self, mock_converters, mock_handler):
        """If an ERROR has no origin, retry should reset the workflow."""
        ui = MockUIBuilder().with_run_again(True).build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}

        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)

        # Simulate a handler returning ERROR on the initial SOURCE_INPUT step.
        # The first run transitions into ERROR, the second run handles the ERROR
        # and (because ask_again is configured True) resets the workflow.
        from unittest.mock import MagicMock
        ui.get_path_input = MagicMock(return_value=ActionResult.error("transient"))

        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)

        controller.run(loop=False)  # SOURCE_INPUT -> sets ERROR
        result = controller.run(loop=False)  # ERROR -> ask_again -> reset

        assert result is True
        assert controller.state_machine.get_state() == WorkflowState.SOURCE_INPUT

# --- migrated from tests/controller/test_coverage_extras.py ---
def make_controller(ui=None):
    ui = ui or MagicMock()
    return ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)


def test_run_once_transitions_to_error_state_on_error_result_extra():
    ui = MagicMock()
    ui.get_path_input.return_value = ActionResult.error("boom")
    controller = make_controller(ui)
    controller.state_machine.state = WorkflowState.SOURCE_INPUT

    # Running a single step should transition to ERROR
    res = controller.run(loop=False)
    assert controller.state_machine.state == WorkflowState.ERROR
    assert controller.state_machine.context.error_message == "boom"

def test_handle_complete_terminate_returns_result_extra():
    ui = MagicMock()
    ui.ask_again.return_value = ActionResult.terminate()
    controller = make_controller(ui)
    controller.state_machine.state = WorkflowState.COMPLETE

    result = controller._handle_complete()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.TERMINATE


def test_handle_error_terminate_returns_result_extra():
    ui = MagicMock()
    ui.ask_again.return_value = ActionResult.terminate()
    controller = make_controller(ui)
    controller.state_machine.state = WorkflowState.ERROR
    controller.state_machine.context.error_message = "boom"

    result = controller._handle_error()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.TERMINATE


def test_handle_error_value_false_returns_terminate_extra():
    ui = MagicMock()
    ui.ask_again.return_value = ActionResult.value(False)
    controller = make_controller(ui)
    controller.state_machine.state = WorkflowState.ERROR
    controller.state_machine.context.error_message = "boom"

    result = controller._handle_error()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.TERMINATE


def test_run_once_handles_back_with_history_extra():
    ui = MagicMock()
    # move state forward so back is possible
    controller = make_controller(ui)
    controller.state_machine.next()  # SOURCE_INPUT -> FORMAT_SELECTION
    # select_output_format will be called in FORMAT_SELECTION
    ui.select_output_format.return_value = ActionResult.back()

    # ensure current state is FORMAT_SELECTION
    controller.state_machine.state = WorkflowState.FORMAT_SELECTION

    res = controller.run(loop=False)
    # back should have been handled and run_once returns True to continue
    assert res is True


def test_run_once_handles_terminate_from_handler_extra():
    ui = MagicMock()
    controller = make_controller(ui)
    controller.state_machine.next()
    controller.state_machine.state = WorkflowState.FORMAT_SELECTION
    ui.select_output_format.return_value = ActionResult.terminate()

    res = controller.run(loop=False)
    assert res is False

def test_handle_complete_value_false_terminates_extra():
    ui = MagicMock()
    ui.ask_again.return_value = ActionResult.value(False)
    controller = make_controller(ui)
    controller.state_machine.state = WorkflowState.COMPLETE

    result = controller._handle_complete()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.TERMINATE


class TestRunOnceExtra:
    """Additional run_once behavior tests migrated from separate file.
    These use only Mock objects for UI interactions.
    """

    def test_run_once_quit_from_ui_stops_loop(self):
        ui = MagicMock()
        ui.get_path_input.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {}, {}, lambda s: None)

        res = controller.run(loop=False)
        assert res is False


    def test_run_once_back_moves_state_back(self):
        ui = MagicMock()
        controller = ConverterController(ui, {}, {}, lambda s: None)
        controller.state_machine.next()  # SOURCE_INPUT -> FORMAT_SELECTION

        ui.select_output_format.return_value = ActionResult.back()

        res = controller.run(loop=False)
        assert res is True
        assert controller.state_machine.get_state().name == 'SOURCE_INPUT'


    def test_run_once_error_sets_error_state(self):
        ui = MagicMock()
        ui.get_path_input.return_value = ActionResult.error("boom")

        controller = ConverterController(ui, {}, {}, lambda s: MockPathBuilder().with_exists(False).build())

        controller.run(loop=False)
        assert controller.state_machine.get_state().name == 'ERROR'
        assert controller.state_machine.context.error_message == 'boom'


    def test_get_files_to_process_quit_returns_empty_list(self):
        ui = MagicMock()
        mock_dir = (
            MockPathBuilder('/dir')
            .with_exists(True)
            .with_is_dir(True)
            .with_files([])
            .build()
        )
        ui.select_files.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {'.pdf': lambda p: None}, {}, lambda s: mock_dir)
        controller.state_machine.context.compatible_files = []
        files = controller._get_files_to_process(mock_dir)
        assert files == []


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
        
        with pytest.raises(KeyError):
            controller._process_single_file(mock_file, 1, MockProgress(), mock_handler, MergeMode.NO_MERGE)
    
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
            mock_dir, mock_handler, accumulator, OutputFormat.JSON, "merged_default"
        )

        assert "merged_default" in filename
        assert ".json" in filename
    
    def test_default_filename_for_file(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: mock_handler}
        controller = ConverterController(ui, mock_converters, handlers, lambda s: None)
        
        mock_file = MockPathBuilder().with_is_dir(False).with_stem("source").build()
        accumulator = ["content"]
        
        filename, size = controller._save_merged_output(
            mock_file, mock_handler, accumulator, OutputFormat.PLAIN_TEXT, "source_merged"
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



class TestActionResultHandling:
    def test_back_from_format_selection_returns_to_previous_state(self, mock_converters, mock_handler):
        ui = MockUIBuilder().build()
        # select_output_format will return a BACK action
        from unittest.mock import MagicMock
        ui.select_output_format = MagicMock(return_value=ActionResult.back())

        controller = ConverterController(ui, mock_converters, {OutputFormat.PLAIN_TEXT: lambda: mock_handler}, lambda s: None)

        # Move state machine to FORMAT_SELECTION (push SOURCE_INPUT on stack)
        controller.state_machine.next()

        # Run one step (FORMAT_SELECTION) and expect it to handle BACK and return True
        result = controller.run(loop=False)

        assert result is True
        assert controller.state_machine.get_state() == WorkflowState.SOURCE_INPUT


    def test_quit_from_files_selection_stops_run(self, mock_converters, mock_handler):
        # Setup UI to return QUIT from select_files
        ui = MockUIBuilder().build()
        ui.select_files = MagicMock(return_value=ActionResult.terminate())

        controller = ConverterController(ui, mock_converters, {OutputFormat.PLAIN_TEXT: lambda: mock_handler}, lambda s: None)

        # Advance state machine to FILES_SELECTION
        controller.state_machine.next()
        controller.state_machine.next()
        controller.state_machine.next()

        # Ensure there is an input_path in context for the handler to inspect
        controller.state_machine.context.input_path = MockPathBuilder().with_is_dir(True).build()
        # Also provide compatible_files since we're bypassing _handle_source_input
        controller.state_machine.context.compatible_files = [
            MockPathBuilder().with_suffix('.pdf').with_stem('x').build()
        ]

        result = controller.run(loop=False)

        assert result is False


    def test_error_from_get_path_input_sets_error_state(self, mock_converters, mock_handler):
        # Make get_path_input return an ERROR action
        ui = MockUIBuilder().build()
        ui.get_path_input = MagicMock(return_value=ActionResult.error("bad path"))

        controller = ConverterController(ui, mock_converters, {OutputFormat.PLAIN_TEXT: lambda: mock_handler}, lambda s: None)

        result = controller.run(loop=False)

        assert result is True
        assert controller.state_machine.get_state() == WorkflowState.ERROR
        assert controller.state_machine.context.error_message == "bad path"


class TestSaveMergedOutputExtra:
    def test_save_merged_output_with_directory_and_file(self, tmp_path):
        ui = MagicMock()
        handlers = {OutputFormat.PLAIN_TEXT: lambda: MagicMock(save=MagicMock(return_value=123))}
        dir_path = MockPathBuilder('/mock/dir').with_is_dir(True).build()

        controller = ConverterController(ui, {}, handlers, lambda s: dir_path)

        handler = handlers[OutputFormat.PLAIN_TEXT]()
        accumulator = ["a", "b"]
        filename, size = controller._save_merged_output(dir_path, handler, accumulator, OutputFormat.PLAIN_TEXT, "merged")

        assert filename.endswith(OutputFormat.PLAIN_TEXT.extension)
        assert size == 123


    def test_save_merged_output_with_file_parent(self):
        ui = MagicMock()
        handlers = {OutputFormat.MARKDOWN: lambda: MagicMock(save=MagicMock(return_value=55))}

        file_path = MockPathBuilder('/mock/file').with_is_dir(False).build()

        controller = ConverterController(ui, {}, handlers, lambda s: file_path)

        handler = handlers[OutputFormat.MARKDOWN]()
        accumulator = ["x"]
        filename, size = controller._save_merged_output(file_path, handler, accumulator, OutputFormat.MARKDOWN, "outname")

        assert filename.endswith(OutputFormat.MARKDOWN.extension)
        assert size == 55


class TestControllerAdditionalBranches:
    """Additional small branch tests moved from temporary file.
    These exercise small branches in `converter_controller` to reach full coverage.
    """

    def test_get_files_to_process_back_returns_empty_list(self):
        ui = MagicMock()
        # directory with one compatible file
        mock_dir = (
            MockPathBuilder('/dir')
            .with_exists(True)
            .with_is_dir(True)
            .with_files([MockPathBuilder().with_suffix('.pdf').with_stem('x').build()])
            .build()
        )
        ui.select_files.return_value = ActionResult.back()

        controller = ConverterController(ui, {'.pdf': lambda p: None}, {}, lambda s: mock_dir)
        # runtime would cache compatible files; test should provide them explicitly
        controller.state_machine.context.compatible_files = [
            MockPathBuilder().with_suffix('.pdf').with_stem('x').build()
        ]
        files = controller._get_files_to_process(mock_dir)
        assert files == []

    def test_merge_mode_prompt_value_sets_merged_filename(self):
        ui = MagicMock()
        ui.select_merge_mode.return_value = ActionResult.value(MergeMode.MERGE)
        ui.prompt_merged_filename.return_value = ActionResult.value('custom_name')

        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)

        result = controller._handle_merge_mode_selection()
        assert result.kind == ActionKind.PROCEED
        assert controller.state_machine.context.merged_filename == 'custom_name'

    def test_complete_nonvalue_ask_again_quits(self):
        ui = MagicMock()
        ui.ask_again.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)
        # move to COMPLETE state
        controller.state_machine.state = WorkflowState.COMPLETE

        res = controller.run(loop=False)
        assert res is False

    def test_get_files_to_process_value_returns_selected_files(self):
        ui = MagicMock()
        
        mock_dir = (
            MockPathBuilder('/dir')
            .with_exists(True)
            .with_is_dir(True)
            .with_files([
                MockPathBuilder().with_suffix('.pdf').with_stem('a').build(),
                MockPathBuilder().with_suffix('.epub').with_stem('b').build(),
                MockPathBuilder().with_suffix('.txt').with_stem('c').build(),
            ])
            .build()
        )
        ui.select_files.return_value = ActionResult.value([0, 1])

        controller = ConverterController(ui, {'.pdf': lambda p: None, '.epub': lambda p: None}, {}, lambda s: mock_dir)
        # runtime would cache compatible files; test should provide them explicitly
        controller.state_machine.context.compatible_files = [
            MockPathBuilder().with_suffix('.pdf').with_stem('a').build(),
            MockPathBuilder().with_suffix('.epub').with_stem('b').build(),
        ]
        files = controller._get_files_to_process(mock_dir)
        assert len(files) == 2
        assert files[0].name == 'a.pdf'
        assert files[1].name == 'b.epub'

    def test_merge_mode_select_nonvalue_returns_quit(self):
        ui = MagicMock()
        ui.select_merge_mode.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)

        res = controller._handle_merge_mode_selection()
        assert res.kind == ActionKind.TERMINATE

    def test_merge_mode_prompt_nonvalue_returns_quit(self):
        ui = MagicMock()
        ui.select_merge_mode.return_value = ActionResult.value(MergeMode.MERGE)
        ui.prompt_merged_filename.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)

        res = controller._handle_merge_mode_selection()
        assert res.kind == ActionKind.TERMINATE

    def test_handle_error_ask_again_nonvalue_returns_quit(self):
        ui = MagicMock()
        ui.ask_again.return_value = ActionResult.terminate()

        controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)
        controller.state_machine.context.error_message = 'boom'
        controller.state_machine.state = WorkflowState.ERROR

        res = controller._handle_error()
        assert res.kind == ActionKind.TERMINATE


def test_handle_source_input_empty_payload_returns_error():
    ui = MagicMock()
    ui.get_path_input.return_value = ActionResult.value("")

    # path factory shouldn't be called when payload is empty, but provide a stub
    controller = make_controller(ui)

    result = controller._handle_source_input()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.ERROR
    assert "provide a source" in result.message


def test_handle_error_with_origin_restores_state():
    ui = MagicMock()
    # ask_again returns a proceed ActionResult
    ui.ask_again.return_value = ActionResult.proceed()

    controller = make_controller(ui)
    # set error context and an origin state
    controller.state_machine.context.error_message = "boom"
    controller.state_machine.context.error_origin = WorkflowState.FORMAT_SELECTION
    controller.state_machine.state = WorkflowState.ERROR

    result = controller._handle_error()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.PROCEED
    # state should be restored to origin
    assert controller.state_machine.get_state() == WorkflowState.FORMAT_SELECTION


def test_run_once_back_without_history_returns_true_and_keeps_state():
    ui = MagicMock()
    ui.get_path_input.return_value = ActionResult.back()

    controller = make_controller(ui)
    # initial state has no back history
    assert controller.state_machine.can_go_back() is False

    res = controller.run(loop=False)
    assert res is True
    assert controller.state_machine.get_state().name == 'SOURCE_INPUT'


def test_handle_error_proceed_with_no_origin_resets_and_returns_proceed():
    ui = MagicMock()
    ui.ask_again.return_value = ActionResult.proceed()

    controller = make_controller(ui)
    controller.state_machine.context.error_message = 'boom'
    controller.state_machine.context.error_origin = None
    controller.state_machine.state = WorkflowState.ERROR

    result = controller._handle_error()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.PROCEED
    # reset should put state back to SOURCE_INPUT
    assert controller.state_machine.get_state() == WorkflowState.SOURCE_INPUT


def test_handle_source_input_unsupported_file_returns_error():
    ui = MagicMock()
    ui.get_path_input.return_value = ActionResult.value("file.docx")

    mock_path = MockPathBuilder().with_is_dir(False).with_suffix('.docx').with_exists(True).build()
    controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: mock_path)

    result = controller._handle_source_input()
    assert isinstance(result, ActionResult)
    assert result.kind == ActionKind.ERROR
    assert "not supported" in result.message


def test_handle_files_selection_value_selects_files():
    ui = MagicMock()
    controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)

    # prepare context as if we are in FILES_SELECTION with a directory input
    controller.state_machine.next()
    controller.state_machine.next()
    controller.state_machine.next()
    controller.state_machine.context.input_path = MockPathBuilder().with_is_dir(True).build()
    p1 = MockPathBuilder().with_suffix('.pdf').with_stem('a').build()
    p2 = MockPathBuilder().with_suffix('.pdf').with_stem('b').build()
    controller.state_machine.context.compatible_files = [p1, p2]

    ui.select_files.return_value = ActionResult.value([1])

    res = controller._handle_files_selection()
    assert res.kind == ActionKind.PROCEED
    assert controller.state_machine.context.files == [p2]


def test_handle_files_selection_no_files_selected_returns_error_and_moves_back():
    ui = MagicMock()
    controller = ConverterController(ui, {}, {OutputFormat.PLAIN_TEXT: lambda: MagicMock()}, lambda s: None)

    # advance to FILES_SELECTION so back() will pop a previous state
    controller.state_machine.next()
    controller.state_machine.next()
    controller.state_machine.next()

    controller.state_machine.context.input_path = MockPathBuilder().with_is_dir(True).build()
    controller.state_machine.context.compatible_files = [MockPathBuilder().with_suffix('.pdf').with_stem('x').build()]

    ui.select_files.return_value = ActionResult.value([])

    res = controller._handle_files_selection()
    assert isinstance(res, ActionResult)
    assert res.kind == ActionKind.ERROR
    assert "no files selected" in res.message



