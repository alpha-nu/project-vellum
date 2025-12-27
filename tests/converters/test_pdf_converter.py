"""Tests for PDFConverter class."""
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from domain.converters.pdf_converter import PDFConverter


class TestPDFConverter:
    """Test PDFConverter with mocked PyMuPDF"""
    
    def test_pdf_text_extraction(self):
        """Test basic PDF text extraction"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page 1 text"
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_reader.open.return_value = mock_doc
        
        # Test
        converter = PDFConverter(Path("test.pdf"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Page 1 text" in result
        mock_reader.open.assert_called_once()
        mock_page.get_text.assert_called_with("text")
    
    def test_pdf_multiple_pages(self):
        """Test PDF with multiple pages"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Page {i + 1} content"
            pages.append(page)
        
        mock_doc.load_page.side_effect = pages
        mock_reader.open.return_value = mock_doc
        
        # Test
        converter = PDFConverter(Path("multi.pdf"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "Page 3 content" in result
        assert mock_doc.load_page.call_count == 3
    
    def test_pdf_ocr_fallback(self):
        """Test OCR fallback for scanned pages"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""  # Empty triggers OCR
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake image bytes"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_reader.open.return_value = mock_doc
        
        # Mock pytesseract and PIL
        with patch('domain.converters.pdf_converter.pytesseract') as mock_tesseract, \
             patch('domain.converters.pdf_converter.Image') as mock_image:
            mock_tesseract.image_to_string.return_value = "OCR extracted text"
            
            # Test
            converter = PDFConverter(Path("scanned.pdf"), reader=mock_reader)
            result = converter.extract_content()
            
            assert "OCR extracted text" in result
            mock_page.get_pixmap.assert_called_once()
            mock_tesseract.image_to_string.assert_called_once()
    
    def test_pdf_with_progress_callback(self):
        """Test progress callback is called correctly"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        pages = [MagicMock() for _ in range(3)]
        for page in pages:
            page.get_text.return_value = "text"
        
        mock_doc.load_page.side_effect = pages
        mock_reader.open.return_value = mock_doc
        
        # Track progress calls
        progress_calls = []
        def progress_cb(current, total):
            progress_calls.append((current, total))
        
        # Test
        converter = PDFConverter(Path("progress.pdf"), reader=mock_reader)
        converter.extract_content(progress_callback=progress_cb)
        
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)
    
    def test_pdf_progress_callback_exception_handling(self):
        """Test that progress callback exceptions don't break extraction"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        
        pages = [MagicMock(), MagicMock()]
        for page in pages:
            page.get_text.return_value = "text"
        
        mock_doc.load_page.side_effect = pages
        mock_reader.open.return_value = mock_doc
        
        # Callback that raises exception
        def bad_callback(current, total):
            raise RuntimeError("Callback error")
        
        # Test - should not raise, extraction continues
        converter = PDFConverter(Path("test.pdf"), reader=mock_reader)
        result = converter.extract_content(progress_callback=bad_callback)
        
        # Extraction should complete despite callback errors
        assert "text" in result
    
    def test_pdf_mixed_content_pages(self):
        """Test PDF with both text and scanned pages"""
        # Setup mock reader and document
        mock_reader = Mock()
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
        mock_reader.open.return_value = mock_doc
        
        # Mock pytesseract and PIL
        with patch('domain.converters.pdf_converter.pytesseract') as mock_tesseract, \
             patch('domain.converters.pdf_converter.Image') as mock_image:
            mock_tesseract.image_to_string.return_value = "OCR page content"
            
            # Test
            converter = PDFConverter(Path("mixed.pdf"), reader=mock_reader)
            result = converter.extract_content()
            
            assert "Digital text page" in result
            assert "OCR page content" in result
            assert "More digital text" in result
            mock_tesseract.image_to_string.assert_called_once()
    
    def test_pdf_converter_per_item(self):
        """Test PDFConverter.extract_content_per_item returns list of pages"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Page {i+1} content"
            pages.append(page)
        
        mock_doc.load_page.side_effect = pages
        mock_reader.open.return_value = mock_doc
        
        # Test
        converter = PDFConverter(Path("test.pdf"), reader=mock_reader)
        result_pages = converter.extract_content_per_item()
        
        assert isinstance(result_pages, list)
        assert len(result_pages) == 3
        assert "Page 1 content" in result_pages[0]
        assert "Page 2 content" in result_pages[1]
        assert "Page 3 content" in result_pages[2]
    
    def test_pdf_converter_per_item_with_progress(self):
        """Test PDFConverter.extract_content_per_item calls progress callback"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2
        
        pages = [MagicMock(), MagicMock()]
        for i, page in enumerate(pages):
            page.get_text.return_value = f"Page {i+1}"
        
        mock_doc.load_page.side_effect = pages
        mock_reader.open.return_value = mock_doc
        
        calls = []
        def progress_cb(current, total):
            calls.append((current, total))
        
        # Test
        converter = PDFConverter(Path("test.pdf"), reader=mock_reader)
        result_pages = converter.extract_content_per_item(progress_callback=progress_cb)
        
        assert len(calls) == 2
        assert calls[0] == (1, 2)
        assert calls[1] == (2, 2)
    
    def test_pdf_converter_per_item_ocr_fallback(self):
        """Test extract_content_per_item with OCR fallback"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""  # Empty page
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"image_data"
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_reader.open.return_value = mock_doc
        
        # Mock pytesseract and PIL
        with patch('domain.converters.pdf_converter.pytesseract') as mock_tesseract, \
             patch('domain.converters.pdf_converter.Image') as mock_image:
            
            # Test
            converter = PDFConverter(Path("ocr_test.pdf"), reader=mock_reader)
            pages = converter.extract_content_per_item()
            assert isinstance(pages, list)
            assert len(pages) == 1
    
    def test_pdf_progress_callback_exception(self):
        """Test PDF converter handles progress callback exceptions"""
        # Setup mock reader and document
        mock_reader = Mock()
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test content"
        mock_doc.load_page.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_reader.open.return_value = mock_doc
        
        def bad_callback(current, total):
            raise RuntimeError("Progress error")
        
        # Test - should not raise despite callback raising
        converter = PDFConverter(Path("test.pdf"), reader=mock_reader)
        pages = converter.extract_content_per_item(progress_callback=bad_callback)
        assert isinstance(pages, list)
        assert len(pages) == 1
