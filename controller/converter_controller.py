"""
Controller for document conversion workflow.

This controller orchestrates the conversion process, handling:
- Batch file processing
- File routing to appropriate converters
- Merge functionality
- Progress tracking coordination
"""
from pathlib import Path
from typing import List, Optional
import time
from view.interface import UIInterface
from model.converters import PDFConverter, EPubConverter
from model.outputs import PlainTextHandler, MarkdownHandler, JSONHandler, OutputHandler
from model.file import File


from enum import Enum


class NextAction(Enum):
    QUIT = 0
    RESTART = 1


class ConverterController:
    """Controller that orchestrates document conversion workflow."""
    
    # Supported file extensions and their converter classes
    CONVERTER_MAP = {
        ".pdf": PDFConverter,
        ".epub": EPubConverter,
    }
    
    # Output format handlers
    FORMAT_HANDLERS = {
        1: PlainTextHandler(),
        2: MarkdownHandler(),
        3: JSONHandler(),
    }
    
    def __init__(self, ui: UIInterface):
        """
        Initialize the controller with a UI interface.
        
        Args:
            ui: UI interface implementing UIInterface abstract class
        """
        self.ui = ui
        
    def get_converter(self, file_path: Path):
        """
        Get appropriate converter for a file based on its extension.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Converter instance or None if extension not supported
        """
        ext = file_path.suffix.lower()
        converter_class = self.CONVERTER_MAP.get(ext)
        return converter_class(file_path) if converter_class else None
    
    def get_compatible_files(self, directory: Path) -> List[Path]:
        """
        Scan directory for compatible files.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of compatible file paths
        """
        return [
            f for f in directory.iterdir() 
            if f.suffix.lower() in self.CONVERTER_MAP.keys()
        ]
    
    def run(self):
        """
        Run the conversion workflow repeatedly while the user opts to restart.
        """
        while self.run_once() == NextAction.RESTART:
            continue

    def run_once(self) -> NextAction:
        """Perform a single conversion workflow run.

        Returns:
            NextAction.RESTART if the user wants to run again, otherwise NextAction.QUIT
        """
        self.ui.draw_header()

        # Get user input
        input_str, format_choice, merge_mode = self.ui.get_user_input()
        input_path = Path(input_str)

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
        handler = self.FORMAT_HANDLERS[format_choice]

        # Calculate total input size
        total_input_size = sum(file.stat().st_size for file in files)

        # Process files
        start_time = time.perf_counter()
        accumulator, output_count, total_output_size = self._process_files(files, handler, merge_mode)

        # Handle output based on merge mode
        merged_filename = None
        if merge_mode == "merge" and accumulator:
            merged_filename, merge_output_size = self._save_merged_output(input_path, handler, accumulator)
            total_output_size += merge_output_size
            output_count = 1  # Override with 1 for merged output

        # Show comprehensive conversion summary
        elapsed = time.perf_counter() - start_time
        self.ui.show_conversion_summary(
            total_files=len(files),
            output_count=output_count,
            merge_mode=merge_mode,
            merged_filename=merged_filename,
            total_runtime=elapsed,
            total_input_size_formatted=File.format_file_size(total_input_size),
            total_output_size_formatted=File.format_file_size(total_output_size)
        )

        # Ask user whether to run another conversion or quit
        try:
            run_again = self.ui.ask_again()
        except Exception:
            # If UI doesn't implement the method, default to quitting
            return NextAction.QUIT

        return NextAction.RESTART if run_again else NextAction.QUIT

    
    def _get_files_to_process(self, input_path: Path) -> List[Path]:
        """
        Determine which files to process based on input path.
        
        Args:
            input_path: User-provided path (file or directory)
            
        Returns:
            List of files to process
        """
        if input_path.is_dir():
            compatible_files = self.get_compatible_files(input_path)
            file_data = [File.from_path(path).to_dict() for path in compatible_files]
            selected_indices = self.ui.select_files(file_data)
            return [compatible_files[i] for i in selected_indices]
        else:
            return [input_path]
    
    def _process_files(
        self, 
        files: List[Path], 
        handler: OutputHandler, 
        merge_mode: str
    ) -> tuple[List[str], int, int]:
        """
        Process all files with progress tracking.
        
        Args:
            files: List of files to process
            handler: Output format handler
            merge_mode: One of "no_merge", "merge", or "per_page"
            
        Returns:
            Tuple of (accumulator, output_count, total_output_size)
            - accumulator: List of accumulated content (empty unless merge_mode == "merge")
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
                
                if content and merge_mode == "merge":
                    accumulator.append(
                        f"\n--- start source: {file.name} ---\n{content}"
                    )
        
        return accumulator, output_count, total_output_size
    
    def _process_single_file(
        self, 
        file: Path, 
        task_id: int, 
        progress, 
        handler: OutputHandler, 
        merge_mode: str
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
            - content: Extracted content if merge_mode == "merge", None otherwise
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
        converter = self.get_converter(file)
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
        if merge_mode == "per_page":
            # Per-page output: extract and save individual pages as separate files
            contents = converter.extract_content_per_item(progress_callback=progress_callback)
            output_size = handler.save_multiple(contents, file, file.name)
            output_count = len(contents)  # Number of pages/chapters
            content = None  # No content to accumulate for merge
        else:
            # Extract content as single string
            content = converter.extract_content(progress_callback=progress_callback)
            
            # Save based on merge mode
            if merge_mode == "no_merge":
                # Save as single file (existing behavior)
                output_size = handler.save(content, file)
                output_count = 1  # One output file per input file
            # If merge_mode == "merge", don't save now, will be merged later
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
        input_path: Path, 
        handler: OutputHandler, 
        accumulator: List[str]
    ) -> tuple[str, int]:
        """
        Save merged output to single file.
        
        Args:
            input_path: Original input path
            handler: Output format handler
            accumulator: List of content strings to merge
            
        Returns:
            Tuple of (filename, output_size)
            - filename: Name of the merged output file
            - output_size: Size of the merged output file
        """
        if input_path.is_dir():
            output_name = input_path / "merged_output"
        else:
            output_name = input_path.with_name(f"{input_path.stem}_merged")
        
        output_size = handler.save("\n\n".join(accumulator), output_name)
        
        return output_name.name, output_size
