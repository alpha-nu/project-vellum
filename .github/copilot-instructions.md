# VELLUM: AI Coding Instructions

## Project Overview
Vellum is a Python-based document extraction engine for PDFs (including scanned images) and ePubs. It features a retro-terminal CLI, batch processing, and multi-format output.

## Architecture & Component Relationships

### Core Design Pattern: Abstract Base Classes
- `core.py` defines two abstract classes that structure the entire system:
  - `BaseConverter`: All document parsers inherit from this (PDFConverter, EPubConverter)
  - `OutputHandler`: All output formatters inherit from this (PlainTextHandler, MarkdownHandler, JSONHandler)
- This pattern enables new converters/handlers to be added by simply inheriting and implementing `extract_content()` or `save()`

### Data Flow
```
main.py → interface.py (CLI) → converters.py (extract) → outputs.py (save)
                                      ↓
                          core.py (abstract classes)
```

### Module Responsibilities
- `main.py`: Orchestrates the workflow - handles batch logic, file routing, and merge functionality
- `interface.py`: CLI using Rich library - retro ASCII styling, file selection, progress tracking
- `converters.py`: Document parsing engines (PyMuPDF for PDFs with Tesseract OCR fallback; BeautifulSoup for ePubs)
- `outputs.py`: Format handlers that transform extracted content with metadata
- `core.py`: Abstract contracts ensuring extensibility

## Key Implementation Patterns

### PDF Extraction (Dual-Engine Approach)
- `PDFConverter.extract_content()`: Tries PyMuPDF text extraction first
- Fallback to Tesseract OCR if page returns no text (scanned/image PDFs)
- OCR conversion: page → pixmap → PIL Image → Tesseract string

### ePub Processing
- EbookLib reads epub container; iterates through items with type=9 (content)
- BeautifulSoup strips HTML/CSS while preserving text flow
- Chapters joined with newlines to maintain structure

### Output Formatting
- Each handler transforms content with source attribution
- PlainTextHandler: Direct text save
- MarkdownHandler: Wraps content with markdown header
- JSONHandler: Creates JSON object with source metadata and content

### Batch & Merge Logic
- Batch mode: Directory scan filters for `.pdf`, `.epub`, `.py` extensions
- User selects files interactively via `select_files()`
- Merge mode: Accumulates extracted text with source delimiters, saves as single file
- Non-merge: Individual output files per source

## Development Setup

### Prerequisites
- Python 3.13+ (project optimized for this version)
- System dependencies: Tesseract OCR (macOS: `brew install tesseract`)
- Docker recommended for complete environment (Tesseract + language data included)

### Running Locally
```bash
pip install -r requirements.txt
python main.py
```

### Docker
```bash
docker build -t vellum-converter .
docker run -it -v "/path/to/docs:/data" vellum-converter
```

## Extension Points

### Adding a New Document Type
1. Create `NewTypeConverter(BaseConverter)` in `converters.py`
2. Implement `extract_content() → str`
3. Update `get_converter()` extension map in `main.py` with new extension
4. Test with batch mode

### Adding Output Format
1. Create `NewFormatHandler(OutputHandler)` in `outputs.py`
2. Implement `save(content: str, destination: Path)`
3. Add to handler dict in `main.py`
4. Update CLI format options in `interface.py`

## Testing Notes
- Batch logic filters files by extension before user sees them
- Merge mode concatenates with `--- START SOURCE: {filename} ---` delimiters
- MarkdownHandler prepends `# SOURCE: {filename}` header
- JSON output includes nested `source` and `content` fields
- Progress bar updates on file processing, not extraction completion

## Good Agent Practices
1. ALWAYS run tests after changes you make
2. ALWAYS make sure the README.md is in sync with every new feature you implement.
3. ALWAYS check test coverage after changes and ensure it never decreases from the current baseline. If coverage drops, add tests to cover the uncovered lines or refactor to maintain coverage.
4. When adding new interactive UI methods that use readchar for input, ensure they are properly tested with mocked input to maintain coverage.