"""
Controller for document conversion workflow.

This controller orchestrates the conversion process, handling:
- Batch file processing
- File routing to appropriate converters
- Merge functionality
- Progress tracking coordination
"""
from typing import List, Optional, Dict, Type, Callable
import time
from controller.path_protocol import PathLike
from view.merge_mode import MergeMode
from view.interface import UIInterface
from view.output_format import OutputFormat
from domain.core.output_handler import OutputHandler
from domain.core.base_converter import BaseConverter
from domain.model.file import File
from enum import Enum
from controller.workflow.state_machine import WorkflowState, WorkflowStateMachine, WorkflowContext


ConverterMap = Dict[str, Type[BaseConverter]]
HandlerMap = Dict[OutputFormat, Type[OutputHandler]]
PathFactory = Callable[[str], PathLike] 

MERGE_SOURCE_DELIMITER = "\n--- start source: {source} ---\n"

class NextAction(Enum):
    QUIT = 0
    RESTART = 1

class ConverterController:
    """Controller that orchestrates document conversion workflow."""
    
    def __init__(
        self, 
        ui: UIInterface,
        converters: ConverterMap,
        handlers: HandlerMap,
        path_factory: PathFactory
    ):
       
        self.ui = ui
        self.converters = converters
        self.handlers = handlers
        self.path_factory = path_factory
        self.state_machine = WorkflowStateMachine()

    def run(self, loop: bool = True):
        """Run the workflow.

        Args:
            loop: If True, run until completion; if False, execute a single state step and
                  return a boolean indicating whether the workflow should continue.

        Returns:
            When `loop` is False, returns True to indicate the caller may continue, or
            False to indicate the workflow should stop. When `loop` is True, returns None.
        """
        def run_once() -> bool:
            self.ui.draw_header()
            current_state = self.state_machine.get_state()

            if current_state == WorkflowState.SOURCE_INPUT:
                self._handle_source_input()
            elif current_state == WorkflowState.FORMAT_SELECTION:
                self._handle_format_selection()
            elif current_state == WorkflowState.MERGE_MODE_SELECTION:
                self._handle_merge_mode_selection()
            elif current_state == WorkflowState.FILES_SELECTION:
                self._handle_files_selection()
            elif current_state == WorkflowState.PROCESSING:
                self._handle_processing()
            elif current_state == WorkflowState.COMPLETE:
                return self._handle_complete()

            return True

        if not loop:
            return run_once()

        # loop == True: run until a step returns False
        while True:
            again = run_once()
            if not again:
                break

    def _get_files_to_process(self, input_path: PathLike) -> List[PathLike]:
        """
        Determine which files to process based on input path.
        
        Args:
            input_path: User-provided path (file or directory)
            
        Returns:
            List of files to process
        """
        if input_path.is_dir():
            compatible_files = self._get_compatible_files(input_path)
            file_data = [File.from_path(path).to_dict() for path in compatible_files]
            selected_indices = self.ui.select_files(file_data)
            return [compatible_files[i] for i in selected_indices]
        else:
            return [input_path]
    
    def _process_files(
        self, 
        files: List[PathLike], 
        handler: OutputHandler, 
        merge_mode: MergeMode
    ) -> tuple[List[str], int, int]:
        """
        Process all files with progress tracking.
        
        Args:
            files: List of files to process
            handler: Output format handler
            merge_mode: MergeMode enum value (NO_MERGE, MERGE, or PER_PAGE)
            
        Returns:
            Tuple of (accumulator, output_count, total_output_size)
            - accumulator: List of accumulated content (empty unless merge_mode == MergeMode.MERGE)
            - output_count: Number of output files/pages/chapters created
            - total_output_size: Total size of all output files created
        """
        accumulator = []
        output_count = 0
        total_output_size = 0
        
        with self.ui.get_progress_bar() as progress:
            # Create progress task for each file
            tasks = {
                file: progress.add_task(
                    "", 
                    total=100, 
                    status="pending", 
                    filename=file.name
                ) 
                for file in files
            }
            
            for file in files:
                content, file_output_count, file_output_size = self._process_single_file(
                    file, 
                    tasks[file], 
                    progress, 
                    handler, 
                    merge_mode
                )
                
                output_count += file_output_count
                total_output_size += file_output_size
                
                if content and merge_mode == MergeMode.MERGE:
                    accumulator.append(
                        MERGE_SOURCE_DELIMITER.format(source=file.name) + content
                    )
        
        return accumulator, output_count, total_output_size
    
    def _process_single_file(
        self, 
        file: PathLike, 
        task_id: int, 
        progress, 
        handler: OutputHandler, 
        merge_mode: MergeMode
    ) -> tuple[Optional[str], int, int]:
        """
        Process a single file with progress tracking.
        
        Args:
            file: File to process
            task_id: Progress bar task ID
            progress: Progress bar instance
            handler: Output format handler
            merge_mode: One of "no_merge", "merge", or "per_page"
            
        Returns:
            Tuple of (content, output_count, output_size)
            - content: Extracted content if merge_mode == MergeMode.MERGE, None otherwise
            - output_count: Number of output files/pages/chapters created for this file
            - output_size: Total size of output files created for this file
        """
        file_start = time.perf_counter()
        
        # Update progress to converting
        progress.update(
            task_id,
            status="converting",
            filename=file.name,
            completed=0,
            start_time=file_start,
        )
        
        # Get converter
        converter = self._get_converter(file)
        if not converter:
            return None, 0, 0
        
        # Create progress callback
        def progress_callback(current, total):
            try:
                pct = int((current / total) * 100) if total else 100
                progress.update(
                    task_id,
                    completed=pct,
                    status="converting",
                    filename=file.name,
                    start_time=file_start,
                )
            except Exception:
                pass
        
        # Extract and save based on merge mode
        output_count = 0
        output_size = 0
        if merge_mode == MergeMode.PER_PAGE:
            # Per-page output: extract and save individual pages as separate files
            contents = converter.extract_content_per_item(progress_callback=progress_callback)
            output_size = handler.save_multiple(contents, file, file.name)
            output_count = len(contents)  # Number of pages/chapters
            content = None  # No content to accumulate for merge
        else:
            # Extract content as single string
            content = converter.extract_content(progress_callback=progress_callback)
            
            # Save based on merge mode
            if merge_mode == MergeMode.NO_MERGE:
                # Save as single file (existing behavior)
                output_size = handler.save(content, file)
                output_count = 1  # One output file per input file
            # If merge_mode == MergeMode.MERGE, don't save now, will be merged later
            # output_count will be set to 1 later for the merged file
        
        # Mark as complete
        file_elapsed = time.perf_counter() - file_start
        progress.update(
            task_id,
            completed=100,
            status="done",
            filename=file.name,
            conversion_time=file_elapsed,
        )
        
        return content, output_count, output_size
    
    def _save_merged_output(
        self, 
        input_path: PathLike, 
        handler: OutputHandler, 
        accumulator: List[str],
        format_choice: OutputFormat,
        merged_filename: Optional[str] = None
    ) -> tuple[str, int]:
        """
        Save merged output to single file.
        
        Args:
            input_path: Original input path
            handler: Output format handler
            accumulator: List of content strings to merge
            merged_filename: Optional custom filename for the merged output (without extension)
            format_choice: OutputFormat choice
            
        Returns:
            Tuple of (filename, output_size)
            - filename: Name of the merged output file with extension
            - output_size: Size of the merged output file
        """
        if merged_filename:
            output_name = input_path / merged_filename if input_path.is_dir() else input_path.with_name(merged_filename)
        elif input_path.is_dir():
            output_name = input_path / "merged_output"
        else:
            output_name = input_path.with_name(f"{input_path.stem}_merged")
        
        output_size = handler.save("\n\n".join(accumulator), output_name)
        
        # Compute the actual filename with extension
        actual_filename = output_name.with_suffix(format_choice.extension).name
        
        return actual_filename, output_size

    def _get_converter(self, file_path: PathLike):
        ext = file_path.suffix.lower()
        converter_class = self.converters.get(ext)
        return converter_class(file_path) if converter_class else None
    
    def _get_compatible_files(self, directory: PathLike) -> List[PathLike]:
        supported_extensions = list(self.converters.keys())
        return [
            f for f in directory.iterdir() 
            if f.suffix.lower() in supported_extensions
        ]
    
    def _get_format_handler(self, format_choice: OutputFormat) -> OutputHandler:
        handler_class = self.handlers.get(format_choice)
        if handler_class is None:
            raise ValueError(f"Unknown output format: {format_choice}")
        return handler_class()

    def _handle_source_input(self):
        input_str = self.ui.get_path_input()
        input_path = self.path_factory(input_str)

        if not input_path.exists():
            self.ui.show_error("fatal error: path not found")
            return 

        self.state_machine.context.input_path = input_path
        self.state_machine.next()

    def _handle_format_selection(self):
        format_choice = self.ui.select_output_format()
        self.state_machine.context.format_choice = format_choice
        self.state_machine.next()

    def _handle_merge_mode_selection(self):
        merge_mode = self.ui.select_merge_mode()
        self.state_machine.context.merge_mode = merge_mode
        if merge_mode == MergeMode.MERGE:
            self.state_machine.context.merged_filename = self.ui.prompt_merged_filename()
        self.state_machine.next()

    def _handle_files_selection(self):
        input_path = self.state_machine.context.input_path
        files = self._get_files_to_process(input_path)
        
        if not files:
            self.ui.show_error("no compatible files found")
            self.state_machine.reset() 
            return

        self.state_machine.context.files = files
        self.ui.clear_and_show_header() 
        self.state_machine.next()

    def _handle_processing(self):
        context = self.state_machine.context
        handler = self._get_format_handler(context.format_choice)
        context.handler = handler

        total_input_size = sum(file.stat().st_size for file in context.files)
        
        start_time = time.perf_counter()
        accumulator, output_count, total_output_size = self._process_files(
            context.files, handler, context.merge_mode
        )

        merged_output_filename = None
        if context.merge_mode == MergeMode.MERGE and accumulator:
            merged_output_filename, merge_output_size = self._save_merged_output(
                context.input_path, handler, accumulator, context.format_choice, context.merged_filename
            )
            total_output_size += merge_output_size
            output_count = 1 

        elapsed = time.perf_counter() - start_time
        
        single_output_filename = None
        if context.merge_mode == MergeMode.NO_MERGE and len(context.files) == 1:
            single_output_filename = context.files[0].with_suffix(context.format_choice.extension).name
        
        self.ui.show_conversion_summary(
            total_files=len(context.files),
            output_count=output_count,
            merge_mode=context.merge_mode,
            merged_filename=merged_output_filename,
            total_runtime=elapsed,
            total_input_size_formatted=File.format_file_size(total_input_size),
            total_output_size_formatted=File.format_file_size(total_output_size),
            single_output_filename=single_output_filename
        )
        self.state_machine.next()


    def _handle_complete(self) -> bool:
        try:
            run_again = self.ui.ask_again()
        except Exception:
            return False

        if run_again:
            self.state_machine.reset()
            return True
        else:
            self.state_machine.next() 
            return False
