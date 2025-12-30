"""File model for representing files in the conversion system."""
from dataclasses import dataclass
from typing import Any


@dataclass
class File:
    """Pure data model representing a file's metadata.

    This dataclass intentionally does not perform filesystem IO. Use an
    adapter or factory in the infra layer (for example,
    `domain.adapters.file_factories.file_from_path`) to construct `File`
    instances from concrete filesystem paths.
    """

    name: str
    size_bytes: int

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                if unit == 'B':
                    return f"{int(size)}{unit}"
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    @property
    def formatted_size(self) -> str:
        return self.format_file_size(self.size_bytes)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'size': self.formatted_size
        }
