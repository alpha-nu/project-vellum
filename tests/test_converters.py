"""Enhanced tests for converter classes to increase coverage.
Tests PDF and ePub converters with mocked dependencies.
"""
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from domain.converters.pdf_converter import PDFConverter
from domain.converters.epub_converter import EPubConverter
from domain.converters.pdf_reader import PyMuPDFReader
from domain.converters.epub_reader import EbookLibReader


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


class TestEPubConverter:
    """Test EPubConverter with mocked ebooklib"""
    
    def test_epub_basic_extraction(self):
        """Test basic ePub content extraction"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        mock_item = MagicMock()
        mock_item.get_type.return_value = 9  # Content type
        mock_item.get_content.return_value = b"<html><body>Chapter 1 text</body></html>"
        mock_book.get_items.return_value = [mock_item]
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Chapter 1 text" in result
        mock_reader.open.assert_called_once()
    
    def test_epub_multiple_chapters(self):
        """Test ePub with multiple chapters"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        items = []
        for i in range(3):
            item = MagicMock()
            item.get_type.return_value = 9
            item.get_content.return_value = f"<html><body>Chapter {i + 1}</body></html>".encode()
            items.append(item)
        
        mock_book.get_items.return_value = items
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("multi.epub"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Chapter 1" in result
        assert "Chapter 2" in result
        assert "Chapter 3" in result
    
    def test_epub_html_cleaning(self):
        """Test that HTML tags are stripped"""
        # Setup mock reader and book
        mock_reader = Mock()
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
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
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
    
    def test_epub_filter_non_content_items(self):
        """Test that only content items (type 9) are processed"""
        # Setup mock reader and book
        mock_reader = Mock()
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
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Content" in result
        # Only content item should be processed
        content_item.get_content.assert_called_once()
        non_content_item1.get_content.assert_not_called()
        non_content_item2.get_content.assert_not_called()
    
    def test_epub_with_progress_callback(self):
        """Test progress callback with ePub"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        items = []
        for i in range(4):
            item = MagicMock()
            item.get_type.return_value = 9
            item.get_content.return_value = f"<p>Chapter {i}</p>".encode()
            items.append(item)
        
        mock_book.get_items.return_value = items
        mock_reader.open.return_value = mock_book
        
        # Track progress
        progress_calls = []
        def progress_cb(current, total):
            progress_calls.append((current, total))
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        converter.extract_content(progress_callback=progress_cb)
        
        assert len(progress_calls) == 4
        assert progress_calls[0] == (1, 4)
        assert progress_calls[3] == (4, 4)
    
    def test_epub_progress_callback_exception_handling(self):
        """Test that progress callback exceptions don't break extraction"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        mock_item = MagicMock()
        mock_item.get_type.return_value = 9
        mock_item.get_content.return_value = b"<html>Content</html>"
        mock_book.get_items.return_value = [mock_item]
        mock_reader.open.return_value = mock_book
        
        # Bad callback
        def bad_callback(current, total):
            raise ValueError("Callback error")
        
        # Test - should complete despite callback errors
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        result = converter.extract_content(progress_callback=bad_callback)
        
        assert "Content" in result
    
    def test_epub_empty_chapters(self):
        """Test ePub with empty chapters"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        item1 = MagicMock()
        item1.get_type.return_value = 9
        item1.get_content.return_value = b"<html><body></body></html>"  # Empty
        
        item2 = MagicMock()
        item2.get_type.return_value = 9
        item2.get_content.return_value = b"<html><body>Actual content</body></html>"
        
        mock_book.get_items.return_value = [item1, item2]
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        result = converter.extract_content()
        
        assert "Actual content" in result


class TestPDFConverterOCREdgeCases:
    """Test OCR fallback edge cases in PDFConverter"""
    
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


class TestEPubConverterEdgeCases:
    """Test EPUB converter edge cases"""
    
    def test_epub_extract_per_item_exception_in_progress(self):
        """Test that exception in progress callback doesn't break extraction"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        item = MagicMock()
        item.get_type.return_value = 9
        item.get_content.return_value = b"<html><body><p>Chapter text</p></body></html>"
        
        mock_book.get_items.return_value = [item]
        mock_reader.open.return_value = mock_book
        
        def bad_callback(current, total):
            raise ValueError("Callback error")
        
        # Test - should not raise even though callback raises
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        chapters = converter.extract_content_per_item(progress_callback=bad_callback)
        assert isinstance(chapters, list)


class TestPerPageConverters:
    """Test extract_content_per_item methods in converters"""
    
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
    
    def test_epub_converter_per_item(self):
        """Test EPubConverter.extract_content_per_item returns list of chapters"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        items = []
        for i in range(2):
            item = MagicMock()
            item.get_type.return_value = 9
            item.get_content.return_value = f"<html><body><h1>Chapter {i + 1}</h1><p>Content of chapter {i + 1}</p></body></html>".encode()
            items.append(item)
        
        mock_book.get_items.return_value = items
        mock_reader.open.return_value = mock_book
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        chapters = converter.extract_content_per_item()
        
        assert isinstance(chapters, list)
        assert len(chapters) == 2
        assert "Content of chapter 1" in chapters[0]
        assert "Content of chapter 2" in chapters[1]
        assert "Chapter 1" in chapters[0]
        assert "Chapter 2" in chapters[1]
    
    def test_epub_converter_per_item_with_progress(self):
        """Test EPubConverter.extract_content_per_item calls progress callback"""
        # Setup mock reader and book
        mock_reader = Mock()
        mock_book = MagicMock()
        
        item = MagicMock()
        item.get_type.return_value = 9
        item.get_content.return_value = b"<html><body><p>Chapter text</p></body></html>"
        
        mock_book.get_items.return_value = [item]
        mock_reader.open.return_value = mock_book
        
        calls = []
        def progress_cb(current, total):
            calls.append((current, total))
        
        # Test
        converter = EPubConverter(Path("test.epub"), reader=mock_reader)
        chapters = converter.extract_content_per_item(progress_callback=progress_cb)
        
        # Progress callback should be called for each content item
        assert len(calls) >= 1
        assert all(current <= total for current, total in calls)
