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
        Main controller workflow.
        
        Orchestrates the entire conversion process:
        1. Display header
        2. Get user input
        3. Validate path
        4. Handle batch or single file
        5. Process files
        6. Handle merge mode (no_merge, merge, or per_page)
        7. Show completion
        """
        self.ui.draw_header()
        
        # Get user input
        input_str, format_choice, merge_mode = self.ui.get_user_input()
        input_path = Path(input_str)
        
        # Validate path
        if not input_path.exists():
            self.ui.show_error("fatal error: path not found")
            return
        
        # Determine files to process
        files = self._get_files_to_process(input_path)
        
        if not files:
            self.ui.show_no_files()
            return
        
        # Clear screen and redraw header before processing
        self.ui.clear_and_show_header()
        
        # Get output handler
        handler = self.FORMAT_HANDLERS[format_choice]
        
        # Process files
        start_time = time.perf_counter()
        accumulator = self._process_files(files, handler, merge_mode)
        
        # Handle output based on merge mode
        if merge_mode == "merge" and accumulator:
            self._save_merged_output(input_path, handler, accumulator)
        
        # Show completion
        elapsed = time.perf_counter() - start_time
        self.ui.show_shutdown(elapsed)
    
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
            file_data = [File(path).to_dict() for path in compatible_files]
            selected_indices = self.ui.select_files(file_data)
            return [compatible_files[i] for i in selected_indices]
        else:
            return [input_path]
    
    def _process_files(
        self, 
        files: List[Path], 
        handler: OutputHandler, 
        merge_mode: str
    ) -> List[str]:
        """
        Process all files with progress tracking.
        
        Args:
            files: List of files to process
            handler: Output format handler
            merge_mode: One of "no_merge", "merge", or "per_page"
            
        Returns:
            List of accumulated content (empty unless merge_mode == "merge")
        """
        accumulator = []
        
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
                content = self._process_single_file(
                    file, 
                    tasks[file], 
                    progress, 
                    handler, 
                    merge_mode
                )
                
                if content and merge_mode == "merge":
                    accumulator.append(
                        f"\n--- start source: {file.name} ---\n{content}"
                    )
        
        return accumulator
    
    def _process_single_file(
        self, 
        file: Path, 
        task_id: int, 
        progress, 
        handler: OutputHandler, 
        merge_mode: str
    ) -> Optional[str]:
        """
        Process a single file with progress tracking.
        
        Args:
            file: File to process
            task_id: Progress bar task ID
            progress: Progress bar instance
            handler: Output format handler
            merge_mode: One of "no_merge", "merge", or "per_page"
            
        Returns:
            Extracted content if merge_mode == "merge", None otherwise
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
            return None
        
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
        if merge_mode == "per_page":
            # Per-page output: extract and save individual pages as separate files
            contents = converter.extract_content_per_item(progress_callback=progress_callback)
            handler.save_multiple(contents, file, file.name)
            content = None  # No content to accumulate for merge
        else:
            # Extract content as single string
            content = converter.extract_content(progress_callback=progress_callback)
            
            # Save based on merge mode
            if merge_mode == "no_merge":
                # Save as single file (existing behavior)
                handler.save(content, file)
            # If merge_mode == "merge", don't save now, will be merged later
        
        # Mark as complete
        file_elapsed = time.perf_counter() - file_start
        progress.update(
            task_id,
            completed=100,
            status="done",
            filename=file.name,
            conversion_time=file_elapsed,
        )
        
        return content
    
    def _save_merged_output(
        self, 
        input_path: Path, 
        handler: OutputHandler, 
        accumulator: List[str]
    ):
        """
        Save merged output to single file.
        
        Args:
            input_path: Original input path
            handler: Output format handler
            accumulator: List of content strings to merge
        """
        if input_path.is_dir():
            output_name = input_path / "merged_output"
        else:
            output_name = input_path.with_name(f"{input_path.stem}_merged")
        
        handler.save("\n\n".join(accumulator), output_name)
        self.ui.show_merge_complete(output_name.name)
