"""
Enhanced tests for converter classes to increase coverage.
Tests PDF and ePub converters with mocked dependencies.
"""
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from model.converters import PDFConverter, EPubConverter


class TestPDFConverter:
    """Test PDFConverter with mocked PyMuPDF"""
    
    @patch('model.converters.fitz')
    def test_pdf_text_extraction(self, mock_fitz):
        """Test basic PDF text extraction"""
        # Setup mock
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page 1 text"
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_fitz.open.return_value = mock_doc
        
        # Test
        converter = PDFConverter(Path("test.pdf"))
        result = converter.extract_content()
        
        assert "Page 1 text" in result
        mock_fitz.open.assert_called_once()
        mock_page.get_text.assert_called_with("text")
    
    @patch('model.converters.fitz')
    def test_pdf_multiple_pages(self, mock_fitz):
        """Test PDF with multiple pages"""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Page {i + 1} content"
            pages.append(page)
        
        mock_doc.load_page.side_effect = pages
        mock_fitz.open.return_value = mock_doc
        
        # Test
        converter = PDFConverter(Path("multi.pdf"))
        result = converter.extract_content()
        
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "Page 3 content" in result
        assert mock_doc.load_page.call_count == 3
    
    @patch('model.converters.pytesseract')
    @patch('model.converters.Image')
    @patch('model.converters.fitz')
    def test_pdf_ocr_fallback(self, mock_fitz, mock_image, mock_tesseract):
        """Test OCR fallback for scanned pages"""
        # Setup mock - empty text triggers OCR
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""  # Empty triggers OCR
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake image bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_fitz.open.return_value = mock_doc
        
        mock_tesseract.image_to_string.return_value = "OCR extracted text"
        
        # Test
        converter = PDFConverter(Path("scanned.pdf"))
        result = converter.extract_content()
        
        assert "OCR extracted text" in result
        mock_page.get_pixmap.assert_called_once()
        mock_tesseract.image_to_string.assert_called_once()
    
    @patch('model.converters.fitz')
    def test_pdf_with_progress_callback(self, mock_fitz):
        """Test progress callback is called correctly"""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        pages = [MagicMock() for _ in range(3)]
        for page in pages:
            page.get_text.return_value = "text"
        
        mock_doc.load_page.side_effect = pages
        mock_fitz.open.return_value = mock_doc
        
        # Track progress calls
        progress_calls = []
        def progress_cb(current, total):
            progress_calls.append((current, total))
        
        # Test
        converter = PDFConverter(Path("progress.pdf"))
        converter.extract_content(progress_callback=progress_cb)
        
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)
    
    @patch('model.converters.fitz')
    def test_pdf_progress_callback_exception_handling(self, mock_fitz):
        """Test that progress callback exceptions don't break extraction"""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        
        pages = [MagicMock(), MagicMock()]
        for page in pages:
            page.get_text.return_value = "text"
        
        mock_doc.load_page.side_effect = pages
        mock_fitz.open.return_value = mock_doc
        
        # Callback that raises exception
        def bad_callback(current, total):
            raise RuntimeError("Callback error")
        
        # Test - should not raise, extraction continues
        converter = PDFConverter(Path("test.pdf"))
        result = converter.extract_content(progress_callback=bad_callback)
        
        # Extraction should complete despite callback errors
        assert "text" in result
    
    @patch('model.converters.pytesseract')
    @patch('model.converters.Image')
    @patch('model.converters.fitz')
    def test_pdf_mixed_content_pages(self, mock_fitz, mock_image, mock_tesseract):
        """Test PDF with both text and scanned pages"""
        # Setup mock
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        # Page 1: has text
        page1 = MagicMock()
        page1.get_text.return_value = "Digital text page"
        
        # Page 2: scanned (empty text)
        page2 = MagicMock()
        page2.get_text.return_value = ""
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake"
        page2.get_pixmap.return_value = mock_pix
        
        # Page 3: has text
        page3 = MagicMock()
        page3.get_text.return_value = "More digital text"
        
        mock_doc.load_page.side_effect = [page1, page2, page3]
        mock_fitz.open.return_value = mock_doc
        mock_tesseract.image_to_string.return_value = "OCR page content"
        
        # Test
        converter = PDFConverter(Path("mixed.pdf"))
        result = converter.extract_content()
        
        assert "Digital text page" in result
        assert "OCR page content" in result
        assert "More digital text" in result
        mock_tesseract.image_to_string.assert_called_once()


class TestEPubConverter:
    """Test EPubConverter with mocked ebooklib"""
    
    @patch('model.converters.epub')
    def test_epub_basic_extraction(self, mock_epub):
        """Test basic ePub content extraction"""
        # Setup mock
        mock_book = MagicMock()
        mock_item = MagicMock()
        mock_item.get_type.return_value = 9  # Content type
        mock_item.get_content.return_value = b"<html><body>Chapter 1 text</body></html>"
        mock_book.get_items.return_value = [mock_item]
        mock_epub.read_epub.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"))
        result = converter.extract_content()
        
        assert "Chapter 1 text" in result
        mock_epub.read_epub.assert_called_once()
    
    @patch('model.converters.epub')
    def test_epub_multiple_chapters(self, mock_epub):
        """Test ePub with multiple chapters"""
        # Setup mock
        mock_book = MagicMock()
        
        items = []
        for i in range(3):
            item = MagicMock()
            item.get_type.return_value = 9
            item.get_content.return_value = f"<html><body>Chapter {i + 1}</body></html>".encode()
            items.append(item)
        
        mock_book.get_items.return_value = items
        mock_epub.read_epub.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("multi.epub"))
        result = converter.extract_content()
        
        assert "Chapter 1" in result
        assert "Chapter 2" in result
        assert "Chapter 3" in result
    
    @patch('model.converters.epub')
    def test_epub_html_cleaning(self, mock_epub):
        """Test that HTML tags are stripped"""
        # Setup mock
        mock_book = MagicMock()
        mock_item = MagicMock()
        mock_item.get_type.return_value = 9
        html_content = b"""
        <html>
            <head><title>Title</title></head>
            <body>
                <h1>Chapter One</h1>
                <p>Paragraph <strong>text</strong> here.</p>
                <div class="note">Note text</div>
            </body>
        </html>
        """
        mock_item.get_content.return_value = html_content
        mock_book.get_items.return_value = [mock_item]
        mock_epub.read_epub.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"))
        result = converter.extract_content()
        
        # Text should be extracted, HTML removed
        assert "Chapter One" in result
        assert "Paragraph" in result
        assert "text" in result
        assert "Note text" in result
        # HTML tags should be gone
        assert "<html>" not in result
        assert "<body>" not in result
        assert "<strong>" not in result
    
    @patch('model.converters.epub')
    def test_epub_filter_non_content_items(self, mock_epub):
        """Test that only content items (type 9) are processed"""
        # Setup mock
        mock_book = MagicMock()
        
        # Mix of item types
        content_item = MagicMock()
        content_item.get_type.return_value = 9
        content_item.get_content.return_value = b"<html><body>Content</body></html>"
        
        non_content_item1 = MagicMock()
        non_content_item1.get_type.return_value = 1  # Not content
        
        non_content_item2 = MagicMock()
        non_content_item2.get_type.return_value = 5  # Not content
        
        mock_book.get_items.return_value = [
            non_content_item1,
            content_item,
            non_content_item2
        ]
        mock_epub.read_epub.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"))
        result = converter.extract_content()
        
        assert "Content" in result
        # Only content item should be processed
        content_item.get_content.assert_called_once()
        non_content_item1.get_content.assert_not_called()
        non_content_item2.get_content.assert_not_called()
    
    @patch('model.converters.epub')
    def test_epub_with_progress_callback(self, mock_epub):
        """Test progress callback with ePub"""
        # Setup mock
        mock_book = MagicMock()
        
        items = []
        for i in range(4):
            item = MagicMock()
            item.get_type.return_value = 9
            item.get_content.return_value = f"<p>Chapter {i}</p>".encode()
            items.append(item)
        
        mock_book.get_items.return_value = items
        mock_epub.read_epub.return_value = mock_book
        
        # Track progress
        progress_calls = []
        def progress_cb(current, total):
            progress_calls.append((current, total))
        
        # Test
        converter = EPubConverter(Path("test.epub"))
        converter.extract_content(progress_callback=progress_cb)
        
        assert len(progress_calls) == 4
        assert progress_calls[0] == (1, 4)
        assert progress_calls[3] == (4, 4)
    
    @patch('model.converters.epub')
    def test_epub_progress_callback_exception_handling(self, mock_epub):
        """Test that progress callback exceptions don't break extraction"""
        # Setup mock
        mock_book = MagicMock()
        mock_item = MagicMock()
        mock_item.get_type.return_value = 9
        mock_item.get_content.return_value = b"<html>Content</html>"
        mock_book.get_items.return_value = [mock_item]
        mock_epub.read_epub.return_value = mock_book
        
        # Bad callback
        def bad_callback(current, total):
            raise ValueError("Callback error")
        
        # Test - should complete despite callback errors
        converter = EPubConverter(Path("test.epub"))
        result = converter.extract_content(progress_callback=bad_callback)
        
        assert "Content" in result
    
    @patch('model.converters.epub')
    def test_epub_empty_chapters(self, mock_epub):
        """Test ePub with empty chapters"""
        # Setup mock
        mock_book = MagicMock()
        
        item1 = MagicMock()
        item1.get_type.return_value = 9
        item1.get_content.return_value = b"<html><body></body></html>"  # Empty
        
        item2 = MagicMock()
        item2.get_type.return_value = 9
        item2.get_content.return_value = b"<html><body>Actual content</body></html>"
        
        mock_book.get_items.return_value = [item1, item2]
        mock_epub.read_epub.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"))
        result = converter.extract_content()
        
        assert "Actual content" in result
