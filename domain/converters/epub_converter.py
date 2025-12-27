"""EPUB document converter."""
from bs4 import BeautifulSoup
from typing import Optional, Callable, List, Any
from domain.core.base_converter import BaseConverter
from .reader_protocols import _EPubReader
from .epub_reader import EbookLibReader


class EPubConverter(BaseConverter):
    """Converter for EPUB documents."""
    
    def __init__(self, source_path, reader: Optional[_EPubReader] = None):
        super().__init__(source_path)
        self._reader: _EPubReader = reader or EbookLibReader()
        self._book = None

    def _load_items(self) -> List[Any]:
        """Load all chapters from EPUB document.
        
        Returns:
            List of EPUB items (content type 9 = readable content)
        """
        self._book = self._reader.open(self.source_path)
        return [it for it in self._book.get_items() if it.get_type() == 9]

    def _extract_from_item(self, item: Any) -> str:
        """Extract text from a single EPUB chapter.
        
        Args:
            item: EPUB item object
        
        Returns:
            Extracted text string
        """
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        return soup.get_text()
