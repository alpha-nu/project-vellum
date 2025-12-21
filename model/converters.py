import fitz  # PyMuPDF
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import io
from typing import Optional, Callable
from model.core import BaseConverter

class PDFConverter(BaseConverter):
    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        doc = fitz.open(self.source_path)
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

class EPubConverter(BaseConverter):
    def extract_content(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
        book = epub.read_epub(self.source_path)
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