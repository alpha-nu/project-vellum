"""Default EPUB reader implementation."""
from ebooklib import epub


class EbookLibReader:
    """Default EPUB reader that opens books via ebooklib."""

    def open(self, path):
        return epub.read_epub(path)
