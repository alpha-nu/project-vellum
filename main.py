"""
Vellum - Document extraction engine for PDFs and ePubs.

Entry point for the application. Delegates all business logic to the controller.
"""
from view.ui import RetroCLI, OutputFormat
from controller.converter_controller import ConverterController
from domain.converters.pdf_converter import PDFConverter
from domain.converters.epub_converter import EPubConverter
from domain.outputs.plain_text_handler import PlainTextHandler
from domain.outputs.markdown_handler import MarkdownHandler
from domain.outputs.json_handler import JSONHandler
from pathlib import Path

converters = {
    ".pdf": PDFConverter,
    ".epub": EPubConverter,
}

handlers = {
    OutputFormat.PLAIN_TEXT: PlainTextHandler,
    OutputFormat.MARKDOWN: MarkdownHandler,
    OutputFormat.JSON: JSONHandler,
}

def main(ui=None):
    ui = ui or RetroCLI()
    controller = ConverterController(
        ui,
        converters=converters,
        handlers=handlers,
        path_factory=Path
    )
    controller.run()


if __name__ == "__main__":
    main()