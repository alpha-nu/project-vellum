"""PDF document converter."""
import pytesseract
from PIL import Image
import io
from typing import Optional, Callable, List, Any
from domain.core.base_converter import BaseConverter
from .reader_protocols import _PDFReader
from .pdf_reader import PyMuPDFReader


class PDFConverter(BaseConverter):
    """Converter for PDF documents with OCR fallback for scanned pages."""
    
    def __init__(self, source_path, reader: Optional[_PDFReader] = None):
        super().__init__(source_path)
        self._reader: _PDFReader = reader or PyMuPDFReader()

    def _load_items(self) -> List[Any]:
        """Load all pages from PDF document."""
        doc = self._reader.open(self.source_path)
        return [doc.load_page(i) for i in range(len(doc))]

    def _extract_from_item(self, page: Any) -> str:
        """Extract text from a single PDF page with OCR fallback.
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            Extracted text string
        """
        text = page.get_text("text").strip()

        # OCR Fallback for scanned/empty pages
        if not text:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)

        return text
