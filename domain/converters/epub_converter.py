"""EPUB document converter."""
from bs4 import BeautifulSoup
from typing import Optional, Callable, List
from domain.core.base_converter import BaseConverter
from .reader_protocols import _EPubReader
from .epub_reader import EbookLibReader


class EPubConverter(BaseConverter):
    """Converter for EPUB documents."""
    
    def __init__(self, source_path, reader: Optional[_EPubReader] = None):
        super().__init__(source_path)
        self._reader: _EPubReader = reader or EbookLibReader()

    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        book = self._reader.open(self.source_path)
        items = [it for it in book.get_items() if it.get_type() == 9]
        chapters = []

        total = len(items)
        for idx, item in enumerate(items):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            chapters.append(soup.get_text())
            if progress_callback:
                try:
                    progress_callback(idx + 1, total)
                except Exception:
                    pass

        return "\n\n".join(chapters)

    def extract_content_per_item(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[str]:
        """Extract EPUB content, one string per chapter."""
        book = self._reader.open(self.source_path)
        items = [it for it in book.get_items() if it.get_type() == 9]
        chapters = []

        total = len(items)
        for idx, item in enumerate(items):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            chapters.append(soup.get_text())
            if progress_callback:
                try:
                    progress_callback(idx + 1, total)
                except Exception:
                    pass

        return chapters
