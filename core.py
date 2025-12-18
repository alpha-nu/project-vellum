import abc
from pathlib import Path

class BaseConverter(metaclass=abc.ABCMeta):
    """Abstract Base Class for all document converters."""
    def __init__(self, source_path: Path):
        self.source_path = source_path

    @abc.abstractmethod
    def extract_content(self) -> str:
        """Extracts raw text from the source file."""
        pass

class OutputHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for different output formats."""
    @abc.abstractmethod
    def save(self, content: str, destination: Path):
        pass