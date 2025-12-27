"""Abstract base class for document converters."""
import abc
from pathlib import Path
from typing import Optional, Callable, List


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
        raise NotImplementedError("Subclasses must implement extract_content()")

    @abc.abstractmethod
    def extract_content_per_item(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[str]:
        """Extracts content from the source file, returning one item per page/chapter.

        Returns:
            List of strings, one per page (PDF) or chapter (EPUB)
        """
        raise NotImplementedError("Subclasses must implement extract_content_per_item()")
