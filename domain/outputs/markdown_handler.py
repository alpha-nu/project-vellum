"""Markdown output handler."""
from pathlib import Path
from typing import List
from domain.core.output_handler import OutputHandler


class MarkdownHandler(OutputHandler):
    """Handler for saving content as markdown files."""
    
    def save(self, content: str, destination: Path) -> int:
        md_content = f"# source: {destination.name}\n\n{content}"
        output_path = destination.with_suffix(".md")
        output_path.write_text(md_content, encoding="utf-8")
        return output_path.stat().st_size

    def save_multiple(self, contents: List[str], destination: Path, source_name: str) -> int:
        """Save each page/chapter as a separate numbered markdown file."""
        stem = destination.stem
        parent = destination.parent
        total_size = 0
        
        for idx, content in enumerate(contents, start=1):
            md_content = f"# source: {source_name} (page {idx})\n\n{content}"
            output_path = parent / f"{stem}_page_{idx}.md"
            output_path.write_text(md_content, encoding="utf-8")
            total_size += output_path.stat().st_size
        
        return total_size
