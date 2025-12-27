import fitz  # PyMuPDF
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import io
from typing import Optional, Callable, List, Any, Protocol
from model.core import BaseConverter


class _PDFReader(Protocol):
    def open(self, path) -> Any:  # pragma: no cover
        ...


class _EPubReader(Protocol):
    def open(self, path) -> Any:  # pragma: no cover
        ...


class PyMuPDFReader:
    """Default PDF reader that opens documents via PyMuPDF."""

    def open(self, path):
        return fitz.open(path)


class EbookLibReader:
    """Default EPUB reader that opens books via ebooklib."""

    def open(self, path):
        return epub.read_epub(path)

class PDFConverter(BaseConverter):
    def __init__(self, source_path, reader: Optional[_PDFReader] = None):
        super().__init__(source_path)
        self._reader: _PDFReader = reader or PyMuPDFReader()

    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        doc = self._reader.open(self.source_path)
        full_text = []

        total = len(doc)
        for page_num in range(total):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()

            # OCR Fallback for scanned/empty pages
            if not text:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img)

            full_text.append(text)

            if progress_callback:
                try:
                    progress_callback(page_num + 1, total)
                except Exception:
                    # Progress callbacks must not raise to avoid breaking extraction
                    pass

        return "\n\n".join(full_text)

    def extract_content_per_item(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> List[str]:
        """Extract PDF content, one string per page."""
        doc = self._reader.open(self.source_path)
        pages = []

        total = len(doc)
        for page_num in range(total):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()

            # OCR Fallback for scanned/empty pages
            if not text:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img)

            pages.append(text)

            if progress_callback:
                try:
                    progress_callback(page_num + 1, total)
                except Exception:
                    pass

        return pages

class EPubConverter(BaseConverter):
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