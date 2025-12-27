"""Abstract base class for document converters."""
import abc
import logging
from pathlib import Path
from typing import Optional, Callable, List, Any

logger = logging.getLogger(__name__)


class BaseConverter(metaclass=abc.ABCMeta):
    """Abstract Base Class for all document converters.
    
    Provides a template for document extraction with common progress callback handling.
    """
    
    def __init__(self, source_path: Path):
        self.source_path = source_path

    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        """Extracts raw text from the source file.
        
        Template method that orchestrates the extraction process:
        1. Load items (pages, chapters, etc.) from the document
        2. Extract text from each item using _extract_from_item()
        3. Join all extracted text
        4. Handle progress callbacks with proper exception logging

        Args:
            progress_callback: Optional callable receiving (current_index, total_count)
                             Called after processing each item
        
        Returns:
            Concatenated text from all items separated by double newlines
        """
        items = self._load_items()
        contents = self._extract_from_items(items, progress_callback)
        return "\n\n".join(contents)

    def extract_content_per_item(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[str]:
        """Extract content as list of strings, one per item (page/chapter).
        
        Args:
            progress_callback: Optional callable receiving (current_index, total_count)
        
        Returns:
            List of strings, one per document item
        """
        items = self._load_items()
        return self._extract_from_items(items, progress_callback)

    def _extract_from_items(self, items: List[Any], progress_callback: Optional[Callable[[int, int], None]]) -> List[str]:
        """Extract text from all items with progress callback handling.
        
        Args:
            items: List of document items to process
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of extracted text strings
        """
        contents = []
        total = len(items)
        
        for idx, item in enumerate(items):
            text = self._extract_from_item(item)
            contents.append(text)
            self._call_progress_callback(progress_callback, idx + 1, total)
        
        return contents

    @staticmethod
    def _call_progress_callback(
        progress_callback: Optional[Callable[[int, int], None]], 
        current: int, 
        total: int
    ) -> None:
        """Execute progress callback with exception handling.
        
        Logs exceptions to prevent callback failures from breaking extraction.
        
        Args:
            progress_callback: Callback to invoke, if provided
            current: Current item count
            total: Total items
        """
        if not progress_callback:
            return
        
        try:
            progress_callback(current, total)
        except Exception as e:
            # Log but don't re-raise to prevent breaking extraction
            logger.error(f"Progress callback error: {e}")

    @abc.abstractmethod
    def _load_items(self) -> List[Any]:
        """Load items (pages, chapters, etc.) from document.
        
        Returns:
            List of document items ready for processing
        """
        raise NotImplementedError("Subclasses must implement _load_items()")

    @abc.abstractmethod
    def _extract_from_item(self, item: Any) -> str:
        """Extract text from a single item.
        
        Args:
            item: Single document item (page, chapter, etc.)
        
        Returns:
            Extracted text string
        """
        raise NotImplementedError("Subclasses must implement _extract_from_item()")
