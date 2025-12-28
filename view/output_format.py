from enum import Enum


class OutputFormat(Enum):
    PLAIN_TEXT = "txt"
    MARKDOWN = "md"
    JSON = "json"

    @property
    def extension(self) -> str:
        return f".{self.value}"

    @property
    def display_name(self) -> str:
        return {
            OutputFormat.PLAIN_TEXT: "plain text",
            OutputFormat.MARKDOWN: "markdown",
            OutputFormat.JSON: "json"
        }[self]

    @property
    def display_hint(self) -> str:
        return f"({self.extension})"