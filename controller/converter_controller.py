"""
Controller for document conversion workflow.

This controller orchestrates the conversion process, handling:
- Batch file processing
- File routing to appropriate converters
- Merge functionality
- Progress tracking coordination
"""
from pathlib import Path
from typing import List, Optional, Dict, Type, Callable, Protocol, Iterator, runtime_checkable
import time
from view.interface import UIInterface
from view.ui import MergeMode, OutputFormat
from domain.core.output_handler import OutputHandler
from domain.core.base_converter import BaseConverter
from domain.model.file import File
from enum import Enum


@runtime_checkable
class PathLike(Protocol):
    """Protocol defining the path operations required by the controller."""
    
    @property
    def suffix(self) -> str: ...
    
    @property
    def stem(self) -> str: ...
    
    @property
    def name(self) -> str: ...
    
    def exists(self) -> bool: ...
    
    def is_dir(self) -> bool: ...
    
    def iterdir(self) -> Iterator["PathLike"]: ...
    
    def with_suffix(self, suffix: str) -> "PathLike": ...
    
    def with_name(self, name: str) -> "PathLike": ...
    
    def stat(self) -> object: ...
    
    def __truediv__(self, other: str) -> "PathLike": ...


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
        """
        Initialize the controller with a UI interface and dependency maps.
        
        Args:
            ui: UI interface implementing UIInterface abstract class
            converters: Dictionary mapping file extensions to converter classes
            handlers: Dictionary mapping OutputFormat to handler classes
            path_factory: Factory for creating Path objects (defaults to pathlib.Path)
        """
        self.ui = ui
        self.converters = converters
        self.handlers = handlers
        self.path_factory = path_factory
        
    def _get_converter(self, file_path: PathLike):
        """
        Get appropriate converter for a file based on its extension.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Converter instance or None if extension not supported
        """
        ext = file_path.suffix.lower()
        converter_class = self.converters.get(ext)
        return converter_class(file_path) if converter_class else None
    
    def _get_compatible_files(self, directory: PathLike) -> List[PathLike]:
        """
        Scan directory for compatible files.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of compatible file paths
        """
        supported_extensions = list(self.converters.keys())
        return [
            f for f in directory.iterdir() 
            if f.suffix.lower() in supported_extensions
        ]
    
    def _get_format_handler(self, format_choice: OutputFormat) -> OutputHandler:
        """
        Factory method for creating output format handlers on-demand.
        
        Args:
            format_choice: The output format to create a handler for
            
        Returns:
            An instance of the appropriate OutputHandler subclass
        """
        handler_class = self.handlers.get(format_choice)
        if handler_class is None:
            raise ValueError(f"Unknown output format: {format_choice}")
        return handler_class()
    
    def run(self):
        """
        Run the conversion workflow repeatedly while the user opts to restart.
        """
        while self._run_once() == NextAction.RESTART:
            continue

    def _run_once(self) -> NextAction:
        """Perform a single conversion workflow run.

        Returns:
            NextAction.RESTART if the user wants to run again, otherwise NextAction.QUIT
        """
        self.ui.draw_header()

        # Get user input
        input_str, format_choice, merge_mode, merged_filename = self.ui.get_user_input()
        input_path = self.path_factory(input_str)

        # Validate path
        if not input_path.exists():
            self.ui.show_error("fatal error: path not found")
            return NextAction.QUIT

        # Determine files to process
        files = self._get_files_to_process(input_path)

        if not files:
            self.ui.show_error("no compatible files found")
            return NextAction.QUIT

        # Clear screen and redraw header before processing
        self.ui.clear_and_show_header()

        # Get output handler
        handler = self._get_format_handler(format_choice)

        # Calculate total input size
        total_input_size = sum(file.stat().st_size for file in files)

        # Process files
        start_time = time.perf_counter()
        accumulator, output_count, total_output_size = self._process_files(files, handler, merge_mode)

        # Handle output based on merge mode
        merged_output_filename = None
        if merge_mode == MergeMode.MERGE and accumulator:
            merged_output_filename, merge_output_size = self._save_merged_output(input_path, handler, accumulator, format_choice, merged_filename)
            total_output_size += merge_output_size
            output_count = 1  # Override with 1 for merged output

        # Show comprehensive conversion summary
        elapsed = time.perf_counter() - start_time
        
        # Compute single output filename for no-merge single file case
        single_output_filename = None
        if merge_mode == MergeMode.NO_MERGE and len(files) == 1:
            single_output_filename = files[0].with_suffix(format_choice.extension).name
        
        self.ui.show_conversion_summary(
            total_files=len(files),
            output_count=output_count,
            merge_mode=merge_mode,
            merged_filename=merged_output_filename,
            total_runtime=elapsed,
            total_input_size_formatted=File.format_file_size(total_input_size),
            total_output_size_formatted=File.format_file_size(total_output_size),
            single_output_filename=single_output_filename
        )

        # Ask user whether to run another conversion or quit
        try:
            run_again = self.ui.ask_again()
        except Exception:
            # If UI doesn't implement the method, default to quitting
            return NextAction.QUIT

        return NextAction.RESTART if run_again else NextAction.QUIT

    
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
