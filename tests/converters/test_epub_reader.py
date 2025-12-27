"""Tests for EbookLibReader class."""
from unittest.mock import patch, MagicMock
from domain.converters.epub_reader import EbookLibReader


class TestEbookLibReader:
    """Test EbookLibReader implementation."""
    
    def test_epub_reader_opens_book(self):
        """Test EbookLibReader opens book using ebooklib"""
        with patch('domain.converters.epub_reader.epub') as mock_epub:
            mock_book = MagicMock()
            mock_epub.read_epub.return_value = mock_book
            
            reader = EbookLibReader()
            result = reader.open("test.epub")
            
            assert result == mock_book
            mock_epub.read_epub.assert_called_once_with("test.epub")
    
    def test_epub_reader_opens_with_path_object(self):
        """Test EbookLibReader opens book with Path object"""
        from pathlib import Path
        
        with patch('domain.converters.epub_reader.epub') as mock_epub:
            mock_book = MagicMock()
            mock_epub.read_epub.return_value = mock_book
            
            reader = EbookLibReader()
            path = Path("test.epub")
            result = reader.open(path)
            
            assert result == mock_book
            mock_epub.read_epub.assert_called_once_with(path)
