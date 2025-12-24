"""File model for representing files in the conversion system."""
from pathlib import Path
from dataclasses import dataclass


@dataclass
class File:
    """Model representing a file with its metadata."""
    
    path: Path
    
    @property
    def name(self) -> str:
        """Get the file name."""
        return self.path.name
    
    @property
    def size_bytes(self) -> int:
        """Get the file size in bytes."""
        return self.path.stat().st_size
    
    @property
    def formatted_size(self) -> str:
        """Get human-readable file size."""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                if unit == 'B':
                    return f"{size}{unit}"
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for view layer."""
        return {
            'name': self.name,
            'size': self.formatted_size
        }
