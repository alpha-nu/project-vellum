"""Tests for PyMuPDFReader class."""
from unittest.mock import patch, MagicMock
from domain.converters.pdf_reader import PyMuPDFReader


class TestPyMuPDFReader:
    """Test PyMuPDFReader implementation."""
    
    def test_pdf_reader_opens_document(self):
        """Test PyMuPDFReader opens document using fitz"""
        with patch('domain.converters.pdf_reader.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_fitz.open.return_value = mock_doc
            
            reader = PyMuPDFReader()
            result = reader.open("test.pdf")
            
            assert result == mock_doc
            mock_fitz.open.assert_called_once_with("test.pdf")
    
    def test_pdf_reader_opens_with_path_object(self):
        """Test PyMuPDFReader opens document with Path object"""
        from pathlib import Path
        
        with patch('domain.converters.pdf_reader.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_fitz.open.return_value = mock_doc
            
            reader = PyMuPDFReader()
            path = Path("test.pdf")
            result = reader.open(path)
            
            assert result == mock_doc
            mock_fitz.open.assert_called_once_with(path)
