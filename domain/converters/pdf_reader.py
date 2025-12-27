"""Default PDF reader implementation."""
import fitz  # PyMuPDF


class PyMuPDFReader:
    """Default PDF reader that opens documents via PyMuPDF."""

    def open(self, path):
        return fitz.open(path)
