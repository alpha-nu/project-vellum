"""
Vellum - Document extraction engine for PDFs and ePubs.

Entry point for the application. Delegates all business logic to the controller.
"""
from view.output_format import OutputFormat
from view.ui import RetroCLI
from view.keyboard import read_char
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
    ui = ui or RetroCLI(keyboard_reader=read_char)
    controller = ConverterController(
        ui,
        converters=converters,
        handlers=handlers,
        path_factory=Path
    )
    controller.run()


if __name__ == "__main__":
    main()