import json
from pathlib import Path
from core import OutputHandler

class PlainTextHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        destination.with_suffix(".txt").write_text(content, encoding="utf-8")

class MarkdownHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        md_content = f"# source: {destination.name}\n\n{content}"
        destination.with_suffix(".md").write_text(md_content, encoding="utf-8")

class JSONHandler(OutputHandler):
    def save(self, content: str, destination: Path):
        data = {"source": str(destination.name), "content": content}
        with open(destination.with_suffix(".json"), 'w') as f:
            json.dump(data, f, indent=4)