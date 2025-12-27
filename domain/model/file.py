"""File model for representing files in the conversion system."""
from pathlib import Path
from dataclasses import dataclass
from typing import Union, Any


@dataclass
class File:
    """Pure data model representing a file's metadata.

    This class no longer performs filesystem IO directly. Use
    `File.from_path()` to construct instances from an actual filesystem path.
    """

    name: str
    size_bytes: int

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "2.5MB")
        """
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
        """Get human-readable file size."""
        return self.format_file_size(self.size_bytes)

    def to_dict(self) -> dict:
        """Convert to dictionary for view layer."""
        return {
            'name': self.name,
            'size': self.formatted_size
        }

    @classmethod
    def from_path(cls, path: Union[Path, Any]) -> 'File':
        """Factory that constructs a File object from a Path-like object.

        The `path` argument must provide a `.name` attribute and a `.stat()` method
        returning an object with `.st_size` attribute (this keeps the factory
        test-friendly by allowing fake path-like objects).
        """
        p = Path(path)
        size = p.stat().st_size
        return cls(name=p.name, size_bytes=size)
