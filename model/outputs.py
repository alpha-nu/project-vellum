import json
from pathlib import Path
from typing import List
from model.core import OutputHandler

class PlainTextHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        destination.with_suffix(".txt").write_text(content, encoding="utf-8")

    def save_multiple(self, contents: List[str], destination: Path, source_name: str):
        """Save each page/chapter as a separate numbered text file."""
        stem = destination.stem
        parent = destination.parent
        
        for idx, content in enumerate(contents, start=1):
            output_path = parent / f"{stem}_page_{idx}.txt"
            output_path.write_text(content, encoding="utf-8")

class MarkdownHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        md_content = f"# source: {destination.name}\n\n{content}"
        destination.with_suffix(".md").write_text(md_content, encoding="utf-8")

    def save_multiple(self, contents: List[str], destination: Path, source_name: str):
        """Save each page/chapter as a separate numbered markdown file."""
        stem = destination.stem
        parent = destination.parent
        
        for idx, content in enumerate(contents, start=1):
            md_content = f"# source: {source_name} (page {idx})\n\n{content}"
            output_path = parent / f"{stem}_page_{idx}.md"
            output_path.write_text(md_content, encoding="utf-8")

class JSONHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        data = {"source": str(destination.name), "content": content}
        with open(destination.with_suffix(".json"), 'w') as f:
            json.dump(data, f, indent=4)

    def save_multiple(self, contents: List[str], destination: Path, source_name: str):
        """Save each page/chapter as a separate numbered JSON file."""
        stem = destination.stem
        parent = destination.parent
        
        for idx, content in enumerate(contents, start=1):
            data = {
                "source": source_name,
                "page": idx,
                "content": content
            }
            output_path = parent / f"{stem}_page_{idx}.json"
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=4)