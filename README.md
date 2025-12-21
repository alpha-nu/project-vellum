# 📟 VELLUM: THE DOCUMENT CONVERTER

Vellum is a high-performance, object-oriented document extraction engine designed with a retro-terminal aesthetic. It transforms PDFs (including scanned images via OCR) and ePubs into clean, structured data.

Vellum is optimized for **Python 3.13**

## 🛠 Features
* **Dual-Engine Parsing:** Uses `PyMuPDF` for digital text and `Tesseract OCR` for scanned/image-based PDFs.
* **ePub Scrubbing:** Deep-cleans ebook containers, stripping HTML/CSS while preserving narrative flow.
* **Batch Processing:** Point the tool at a directory, and it will automatically detect and process all compatible files.
* **Smart Merging:** Optional feature to consolidate an entire library into a single master file with source headers.
* **Multi-Format Output:** Export to Plain Text (`.txt`), Markdown (`.md`), or JSON (`.json`).
* **8-Bit Aesthetic:** A visual CLI built for the dark-mode purist, featuring ASCII art and progress tracking.
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

Once launched, the "System Ready" prompt will guide you through the conversion:

1.  **INPUT_PATH:** * Provide a specific file path (e.g., `/data/book.pdf`).
    * Provide a directory path (e.g., `/data`) to trigger **Batch Mode**.
2.  **SELECT_FORMAT:** Choose between `.txt`, `.md`, or `.json`.
3.  **MERGE_PROMPT:** If you are processing a directory, you will be asked if you want to merge all outputs into a single file. 
    * `Y`: Creates one "Master" file containing all extracted text with separators.
    * `N`: Creates individual output files for every source document.

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

Vellum follows **MVC architecture** with full unit test coverage:

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Test structure:**
- `tests/test_model.py` — Model layer (converters, extractors)
- `tests/test_view.py` — View layer (UI components)
- `tests/test_controller.py` — Controller layer (orchestration)

See [`TESTING.md`](TESTING.md) for detailed testing documentation and examples.

---

## 🏗 Architecture

Vellum implements **Model-View-Controller (MVC)** separation:

- **Model** (`model/core.py`, `model/converters.py`, `model/outputs.py`) — Business logic and document extraction
- **View** (`view/ui.py`, `view/interface.py`) — UI rendering and user interaction
- **Controller** (`main.py`) — Orchestration with dependency injection

This architecture ensures:
- ✅ Separation of concerns
- ✅ Independent unit testing of each layer
- ✅ Easy extensibility for new formats and outputs

---

## 📄 License

[View License](LICENSE)