from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from view.keyboard import read_keyboard_key


class UIInterface(ABC):
    """Abstract interface for the UI/View layer to facilitate testing and
    dependency injection.
    """

    def __init__(self, keyboard_reader: Optional[Callable] = None):
        """Initialize UIInterface with optional keyboard reader dependency.
        
        Args:
            keyboard_reader: Optional callable that returns KeyboardToken on each call.
                           If not provided, the default read_keyboard_key will be used.
        """
        self.keyboard_reader = keyboard_reader or read_keyboard_key

    @abstractmethod
    def print_center(self, renderable):
        pass

    @abstractmethod
    def input_center(self, prompt_symbol: str = ">>: ") -> str:
        pass

    @abstractmethod
    def draw_header(self):
        pass

    @abstractmethod
    def clear_and_show_header(self):
        pass

    @abstractmethod
    def select_files(self, file_data: List[Dict[str, Any]]) -> List[int]:
        """Display file selector and return indices of selected files.
        
        Args:
            file_data: List of dicts with 'name' and 'size' keys
            
        Returns:
            List of selected file indices
        """
        pass

    @abstractmethod
    def get_user_input(self):
        pass

    @abstractmethod
    def get_progress_bar(self):
        pass

    @abstractmethod
    def print_panel(self, content: str, content_color_key: str = "prompt"):
        pass

    @abstractmethod
    def show_error(self, message: str):
        pass

    @abstractmethod
    def show_conversion_summary(
        self, 
        total_files: int, 
        output_count: int, 
        merge_mode: str, 
        merged_filename: Optional[str], 
        total_runtime: float, 
        total_input_size_formatted: str,
        total_output_size_formatted: str,
        single_output_filename: Optional[str] = None
    ):
        """Display comprehensive conversion summary and completion message.
        
        Args:
            total_files: Number of input files processed
            output_count: Number of output files/pages/chapters created
            merge_mode: One of "no_merge", "merge", or "per_page"
            merged_filename: Name of merged output file (if merge_mode == "merge")
            total_runtime: Total conversion time in seconds
            total_input_size_formatted: Formatted total size of input files (e.g., "2.5MB")
        """
        pass
