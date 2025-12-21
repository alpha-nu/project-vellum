from abc import ABC, abstractmethod
from typing import List
from pathlib import Path


class UIInterface(ABC):
    """Abstract interface for the UI/View layer to facilitate testing and
    dependency injection.
    """

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
    def select_files(self, files: List[Path]) -> List[Path]:
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
    def show_no_files(self):
        pass

    @abstractmethod
    def show_merge_complete(self, output_name: str):
        pass

    @abstractmethod
    def show_shutdown(self, elapsed_seconds: float):
        pass
