"""PDF and EPUB reader protocols for dependency injection."""
from typing import Protocol, Any


class _PDFReader(Protocol):
    """Protocol for PDF reader implementations."""
    def open(self, path) -> Any:  # pragma: no cover
        ...


class _EPubReader(Protocol):
    """Protocol for EPUB reader implementations."""
    def open(self, path) -> Any:  # pragma: no cover
        ...
