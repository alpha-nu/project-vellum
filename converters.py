import fitz  # PyMuPDF
from ebooklib import epub
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import io
from core import BaseConverter

class PDFConverter(BaseConverter):
    def extract_content(self) -> str:
        doc = fitz.open(self.source_path)
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            
            # OCR Fallback for scanned/empty pages
            if not text:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img)
            
            full_text.append(text)
        
        return "\n\n".join(full_text)

class EPubConverter(BaseConverter):
    def extract_content(self) -> str:
        book = epub.read_epub(self.source_path)
        chapters = []
        
        for item in book.get_items():
            # item_type 9 is the document/content type in EbookLib
            if item.get_type() == 9:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                chapters.append(soup.get_text())
                
        return "\n\n".join(chapters)