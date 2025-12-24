```
    ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
    ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
    ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
    ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
     ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
      ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
```

# THE DOCUMENT CONVERTER

[![Tests](https://github.com/alpha-nu/project-vellum/actions/workflows/test.yml/badge.svg)](https://github.com/alpha-nu/project-vellum/actions/workflows/test.yml)
[![Coverage](https://alpha-nu.github.io/project-vellum/coverage/badge.svg)](https://alpha-nu.github.io/project-vellum/coverage/)

Vellum is a high-performance, object-oriented document extraction engine designed with a retro-terminal aesthetic. It transforms PDFs (including scanned images via OCR) and ePubs into clean, structured data.

Vellum is optimized for **Python 3.13**

## 🛠 Features
* **Dual-Engine Parsing:** Uses `PyMuPDF` for digital text and `Tesseract OCR` for scanned/image-based PDFs.
* **ePub Scrubbing:** Deep-cleans ebook containers, stripping HTML/CSS while preserving narrative flow.
* **Batch Processing:** Interactive file selector for directories - navigate and select files with keyboard controls.
* **Per-Page/Chapter Output:** Extract each PDF page or ePub chapter as separate files.
* **Smart Merging:** Consolidate multiple documents into a single master file with source attribution.
* **Multi-Format Output:** Export to Plain Text (`.txt`), Markdown (`.md`), or JSON (`.json`).
* **Interactive CLI:** Retro-styled terminal interface with ASCII art, navigation controls, and real-time progress tracking.
* **File Size Display:** See document sizes during selection for informed batch processing.
* **Dockerized:** Fully containerized to handle complex system dependencies (Tesseract/Leptonica) out of the box.

---

## 🚀 Quick Start (Docker)

Docker is the recommended way to run Vellum, as it packages the Tesseract OCR engine and all language training data.

1.  **Build the Image:**
    ```bash
    docker build -t vellum-converter .
    ```

2.  **Run with Volume Mapping:**
    Map your local folder containing your documents to the container's `/data` directory.
    ```bash
    docker run -it -v "/path/to/your/docs:/data" vellum-converter
    ```

---

## 📖 CLI Workflow

Once launched, Vellum's interactive interface guides you through the conversion:

1. **Input Path:** 
   - Provide a specific file path (e.g., `/data/book.pdf`)
   - Provide a directory path (e.g., `/data`) to trigger **Batch Mode**

2. **Output Format:** 
   - Choose between Plain Text (`.txt`), Markdown (`.md`), or JSON (`.json`)

3. **File Selection** (Batch Mode only):
   - Navigate files with ⬆︎ /⬇︎ arrow keys
   - Toggle selection with `SPACE`
   - Select all with `A`, quit with `Q`
   - Confirm with `ENTER`
   - Files display with sizes for reference

4. **Merge Mode:**
   - **No merge:** Individual output file per source document
   - **Merge:** Combine all into single file with source headers
   - **File per page:** One output file per PDF page or ePub chapter

---

## 💻 Local Development

If you prefer to run the code natively:

### 1. Install System Dependencies
* **Tesseract OCR:** * *macOS:* `brew install tesseract`
    * *Linux:* `sudo apt install tesseract-ocr`
    * *Windows:* Install via the [UB-Mannheim binary](https://github.com/UB-Mannheim/tesseract/wiki).

### 2. Install Python Requirements
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python main.py
```

---

## 🧪 Testing

Vellum follows **MVC architecture** with comprehensive unit test coverage (98%+) and automated testing on every commit.

### Running Tests Locally

**Run all tests with coverage:**
```bash
pytest tests/ -v --cov=. --cov-report=term --cov-report=html
```

**Run specific test modules:**
```bash
pytest tests/test_controller.py -v    # Controller layer
pytest tests/test_converters.py -v    # Document converters
pytest tests/test_outputs.py -v       # Output formatters
pytest tests/test_view.py -v          # UI components
pytest tests/test_model.py -v         # Model utilities
```

**Quick test run (no coverage):**
```bash
pytest tests/ -v --no-cov
```

### Test Structure

```
tests/
├── test_controller.py    # Controller orchestration and workflow
├── test_converters.py    # PDF/ePub extraction engines
├── test_outputs.py       # Plain text, Markdown, JSON handlers
├── test_view.py          # CLI interface and user interactions
└── test_model.py         # Model layer utilities
```

### Coverage Reports

Tests automatically generate coverage reports in multiple formats:

**1. Terminal Report**
- Displays during test execution
- Shows coverage percentage per file
- Lists uncovered line numbers

**2. HTML Report** (Interactive)
- Located in `htmlcov/` directory
- Line-by-line coverage visualization
- Color-coded: Green (covered) / Red (missing)

```bash
# Open HTML coverage report
open htmlcov/index.html          # macOS
xdg-open htmlcov/index.html      # Linux
start htmlcov/index.html         # Windows
```

**3. XML Report** (CI/CD)
- Located at `coverage.xml`
- Used by GitHub Actions workflow

### CI/CD Integration

GitHub Actions automatically:
- ✅ Runs full test suite on every commit to `main`
- ✅ Generates coverage reports
- ✅ Publishes coverage to GitHub Pages: [View Coverage](https://alpha-nu.github.io/project-vellum/coverage/)
- ✅ Updates coverage badge in README

**Workflow file:** `.github/workflows/test.yml`

### Coverage Configuration

Configured via `pytest.ini` and `.coveragerc`:
- Tracks: `model/`, `view/`, `controller/` modules
- Excludes: test files, virtual environments, `__pycache__`
- Reports: terminal, HTML, XML formats

---

## 🏗 Architecture

Vellum implements **Model-View-Controller (MVC)** with strict separation of concerns:

### Project Structure

```
vellum/
├── main.py                      # Entry point
├── controller/
│   └── converter_controller.py  # Orchestration logic
├── model/
│   ├── core.py                  # Abstract base classes
│   ├── converters.py            # PDF/ePub extraction engines
│   ├── outputs.py               # Format handlers
│   └── file.py                  # File model with metadata
├── view/
│   ├── interface.py             # UI interface contract
│   └── ui.py                    # Rich-based terminal UI
└── tests/
    ├── test_controller.py       # Controller tests
    ├── test_converters.py       # Converter tests
    ├── test_outputs.py          # Output handler tests
    ├── test_view.py             # UI tests
    └── test_model.py            # Model utilities tests
```

### Design Patterns

- **MVC Architecture:** Clean separation between business logic, UI, and orchestration
- **Abstract Base Classes:** `BaseConverter` and `OutputHandler` enable easy extension
- **Dependency Injection:** Controller receives UI interface for testability
- **Model Layer:** `File` model encapsulates file metadata and presentation logic
- **View Passivity:** UI only displays primitive data, no business logic

### Extensibility

**Adding a new document type:**
1. Create `NewTypeConverter(BaseConverter)` in `model/converters.py`
2. Implement `extract_content() → str`
3. Update `CONVERTER_MAP` in `controller/converter_controller.py`

**Adding a new output format:**
1. Create `NewFormatHandler(OutputHandler)` in `model/outputs.py`
2. Implement `save(content: str, destination: Path)`
3. Update `FORMAT_HANDLERS` in `controller/converter_controller.py`
4. Update UI format options in `view/ui.py`

---

## 📄 License

[View License](LICENSE)