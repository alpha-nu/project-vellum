"""Plain text output handler."""
from pathlib import Path
from typing import List
from domain.core.output_handler import OutputHandler


class PlainTextHandler(OutputHandler):
    """Handler for saving content as plain text files."""
    
    def save(self, content: str, destination: Path) -> int:
        output_path = destination.with_suffix(".txt")
        output_path.write_text(content, encoding="utf-8")
        return output_path.stat().st_size

    def save_multiple(self, contents: List[str], destination: Path, source_name: str) -> int:
        """Save each page/chapter as a separate numbered text file."""
        stem = destination.stem
        parent = destination.parent
        total_size = 0
        
        for idx, content in enumerate(contents, start=1):
            output_path = parent / f"{stem}_page_{idx}.txt"
            output_path.write_text(content, encoding="utf-8")
            total_size += output_path.stat().st_size
        
        return total_size
