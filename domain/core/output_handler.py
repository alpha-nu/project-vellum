"""Abstract base class for output handlers."""
import abc
from pathlib import Path
from typing import List


class OutputHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for different output formats."""
    @abc.abstractmethod
    def save(self, content: str, destination: Path):
        raise NotImplementedError("Subclasses must implement save()")

    @abc.abstractmethod
    def save_multiple(self, contents: List[str], destination: Path, source_name: str):
        """Save multiple content pieces (pages/chapters) as separate numbered files.
        
        Args:
            contents: List of content strings to save
            destination: Base path for output files
            source_name: Original source file name for naming output files
        """
        raise NotImplementedError("Subclasses must implement save_multiple()")
