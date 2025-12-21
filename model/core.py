import abc
from pathlib import Path
from typing import Optional, Callable

class BaseConverter(metaclass=abc.ABCMeta):
    """Abstract Base Class for all document converters."""
    def __init__(self, source_path: Path):
        self.source_path = source_path

    @abc.abstractmethod
    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """Extracts raw text from the source file.

        `progress_callback` is an optional callable that receives `(current, total)`
        so callers can surface per-page or per-item progress. Implementations
        must accept the parameter but may ignore it.
        """
        pass

class OutputHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for different output formats."""
    @abc.abstractmethod
    def save(self, content: str, destination: Path):
        pass