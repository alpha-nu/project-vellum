from pathlib import Path

from controller.converter_controller import ConverterController


class FakeUI:
    def __init__(self, tmp_file: Path):
        self._tmp = tmp_file
        self.colors = {
            "prompt": "white",
            "progress": "cyan",
            "options": "cyan",
            "confirm": "green",
        }

    def draw_header(self):
        pass

    def get_user_input(self):
        # return path_str, format_choice(1=plain), merge(False)
        return str(self._tmp), 1, False

    def select_files(self, files):
        return files

    def get_progress_bar(self):
        class FakeProgress:
            def __init__(self):
                self.tasks = {}

            def add_task(self, desc, total=100, **fields):
                tid = len(self.tasks) + 1
                self.tasks[tid] = {"desc": desc, "completed": 0, **fields}
                return tid

            def update(self, tid, **kwargs):
                self.tasks[tid].update(kwargs)

        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            yield FakeProgress()

        return _ctx()

    def print_panel(self, *a, **k):
        pass

    def show_error(self, *a, **k):
        pass

    def show_no_files(self, *a, **k):
        pass

    def show_merge_complete(self, *a, **k):
        pass

    def show_shutdown(self, *a, **k):
        pass


class FakeConverter:
    def __init__(self, path):
        self.path = path

    def extract_content(self, progress_callback=None):
        if progress_callback:
            progress_callback(1, 1)
        return "dummy"


def test_main_controller_flow(tmp_path, monkeypatch):
    # create dummy file
    tmp_file = tmp_path / "doc.pdf"
    tmp_file.write_text("pdf content")

    # monkeypatch get_converter to return FakeConverter
    monkeypatch.setattr(
        "controller.converter_controller.ConverterController.get_converter", 
        lambda self, p: FakeConverter(p)
    )

    ui = FakeUI(tmp_file)
    controller = ConverterController(ui)

    # run controller
    controller.run()

    # verify output file was written by PlainTextHandler
    out = tmp_file.with_suffix('.txt')
    assert out.exists()
    assert out.read_text() == "dummy"


def test_controller_invalid_path(tmp_path):
    """Test controller with non-existent path"""
    class ErrorCapturingUI(FakeUI):
        def __init__(self, path):
            super().__init__(path)
            self.error_shown = False
        
        def show_error(self, message):
            self.error_shown = True
            self.error_message = message
    
    nonexistent = tmp_path / "nonexistent.pdf"
    ui = ErrorCapturingUI(nonexistent)
    controller = ConverterController(ui)
    
    controller.run()
    
    assert ui.error_shown
    assert "not found" in ui.error_message.lower()


def test_controller_directory_mode(tmp_path, monkeypatch):
    """Test controller batch processing a directory"""
    # Create test files
    (tmp_path / "file1.pdf").write_text("content1")
    (tmp_path / "file2.epub").write_text("content2")
    (tmp_path / "file3.txt").write_text("content3")  # Not compatible
    
    class DirUI(FakeUI):
        def __init__(self, directory):
            super().__init__(directory)
            self.selected = []
        
        def get_user_input(self):
            return str(self._tmp), 1, False
        
        def select_files(self, files):
            self.selected = files
            return files  # Select all
    
    monkeypatch.setattr(
        "controller.converter_controller.ConverterController.get_converter",
        lambda self, p: FakeConverter(p)
    )
    
    ui = DirUI(tmp_path)
    controller = ConverterController(ui)
    controller.run()
    
    # Should have found only .pdf and .epub files
    assert len(ui.selected) == 2
    assert any(f.name == "file1.pdf" for f in ui.selected)
    assert any(f.name == "file2.epub" for f in ui.selected)


def test_controller_merge_mode(tmp_path, monkeypatch):
    """Test controller with merge enabled"""
    file1 = tmp_path / "file1.pdf"
    file2 = tmp_path / "file2.pdf"
    file1.write_text("content1")
    file2.write_text("content2")
    
    class MergeUI(FakeUI):
        def __init__(self, directory):
            super().__init__(directory)
            self.merge_complete_called = False
        
        def get_user_input(self):
            return str(self._tmp), 1, True  # Enable merge
        
        def select_files(self, files):
            return files
        
        def show_merge_complete(self, output_name):
            self.merge_complete_called = True
    
    monkeypatch.setattr(
        "controller.converter_controller.ConverterController.get_converter",
        lambda self, p: FakeConverter(p)
    )
    
    ui = MergeUI(tmp_path)
    controller = ConverterController(ui)
    controller.run()
    
    assert ui.merge_complete_called
    # Check merged file was created
    merged_file = tmp_path / "merged_output.txt"
    assert merged_file.exists()
    content = merged_file.read_text()
    assert "file1.pdf" in content
    assert "file2.pdf" in content


def test_controller_no_compatible_files(tmp_path):
    """Test controller with directory containing no compatible files"""
    # Create only incompatible files
    (tmp_path / "file.txt").write_text("text")
    (tmp_path / "file.docx").write_text("doc")
    
    class NoFilesUI(FakeUI):
        def __init__(self, directory):
            super().__init__(directory)
            self.no_files_shown = False
        
        def get_user_input(self):
            return str(self._tmp), 1, False
        
        def select_files(self, files):
            return []  # User selects nothing
        
        def show_no_files(self):
            self.no_files_shown = True
    
    ui = NoFilesUI(tmp_path)
    controller = ConverterController(ui)
    controller.run()
    
    assert ui.no_files_shown


def test_controller_different_formats(tmp_path, monkeypatch):
    """Test controller with different output formats"""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("content")
    
    monkeypatch.setattr(
        "controller.converter_controller.ConverterController.get_converter",
        lambda self, p: FakeConverter(p)
    )
    
    # Test each format
    for format_choice, expected_ext in [(1, ".txt"), (2, ".md"), (3, ".json")]:
        class FormatUI(FakeUI):
            def get_user_input(self):
                return str(test_file), format_choice, False
        
        ui = FormatUI(test_file)
        controller = ConverterController(ui)
        controller.run()
        
        output_file = test_file.with_suffix(expected_ext)
        assert output_file.exists()
        output_file.unlink()  # Clean up for next iteration


def test_controller_get_converter():
    """Test get_converter method"""
    ui = FakeUI(Path("dummy"))
    controller = ConverterController(ui)
    
    # Test PDF
    pdf_path = Path("test.pdf")
    converter = controller.get_converter(pdf_path)
    assert converter is not None
    assert converter.__class__.__name__ == "PDFConverter"
    
    # Test ePub
    epub_path = Path("test.epub")
    converter = controller.get_converter(epub_path)
    assert converter is not None
    assert converter.__class__.__name__ == "EPubConverter"
    
    # Test unsupported
    txt_path = Path("test.txt")
    converter = controller.get_converter(txt_path)
    assert converter is None


def test_controller_get_compatible_files(tmp_path):
    """Test get_compatible_files method"""
    # Create mixed files
    (tmp_path / "file1.pdf").write_text("content")
    (tmp_path / "file2.epub").write_text("content")
    (tmp_path / "file3.txt").write_text("content")
    (tmp_path / "file4.PDF").write_text("content")  # Uppercase
    
    ui = FakeUI(Path("dummy"))
    controller = ConverterController(ui)
    
    compatible = controller.get_compatible_files(tmp_path)
    
    assert len(compatible) == 3  # .pdf, .epub, .PDF
    names = [f.name for f in compatible]
    assert "file1.pdf" in names
    assert "file2.epub" in names
    assert "file4.PDF" in names
    assert "file3.txt" not in names
