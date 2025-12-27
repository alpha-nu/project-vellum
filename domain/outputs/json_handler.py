"""JSON output handler."""
import json
from pathlib import Path
from typing import List
from domain.core.output_handler import OutputHandler


class JSONHandler(OutputHandler):
    """Handler for saving content as JSON files."""
    
    def save(self, content: str, destination: Path) -> int:
        data = {"source": str(destination.name), "content": content}
        output_path = destination.with_suffix(".json")
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=4)
        return output_path.stat().st_size

    def save_multiple(self, contents: List[str], destination: Path, source_name: str) -> int:
        """Save each page/chapter as a separate numbered JSON file."""
        stem = destination.stem
        parent = destination.parent
        total_size = 0
        
        for idx, content in enumerate(contents, start=1):
            data = {
                "source": source_name,
                "page": idx,
                "content": content
            }
            output_path = parent / f"{stem}_page_{idx}.json"
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=4)
            total_size += output_path.stat().st_size
        
        return total_size
