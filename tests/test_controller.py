from pathlib import Path

from controller.converter_controller import ConverterController


class FakeUI:
    def __init__(self, tmp_file: Path):
        self._tmp = tmp_file
        self.colors = {
            "primary": "white",
            "accented": "cyan",
            "secondary": "cyan",
            "confirm": "green",
        }

    def draw_header(self):
        pass

    def clear_and_show_header(self):
        pass

    def get_user_input(self):
        # return path_str, format_choice(1=plain), merge_mode("no_merge")
        return str(self._tmp), 1, "no_merge"

    def select_files(self, file_data):
        # Return all indices (select all files)
        return list(range(len(file_data)))

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

    def show_conversion_summary(self, *a, **k):
        pass


class FakeConverter:
    def __init__(self, path):
        self.path = path

    def extract_content(self, progress_callback=None):
        if progress_callback:
            progress_callback(1, 1)
        return "dummy"
    
    def extract_content_per_item(self, progress_callback=None):
        if progress_callback:
            progress_callback(1, 1)
        return ["page1", "page2", "page3"]


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
        
        def select_files(self, file_data):
            self.selected = file_data
            return list(range(len(file_data)))  # Select all
    
    monkeypatch.setattr(
        "controller.converter_controller.ConverterController.get_converter",
        lambda self, p: FakeConverter(p)
    )
    
    ui = DirUI(tmp_path)
    controller = ConverterController(ui)
    controller.run()
    
    # Should have found only .pdf and .epub files
    assert len(ui.selected) == 2
    assert any(f['name'] == "file1.pdf" for f in ui.selected)
    assert any(f['name'] == "file2.epub" for f in ui.selected)


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
            return str(self._tmp), 1, "merge"  # Enable merge
        
        def select_files(self, file_data):
            return list(range(len(file_data)))
        
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
        
        def select_files(self, file_data):
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
                return str(test_file), format_choice, "no_merge"
        
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


class TestControllerEdgeCases:
    """Test controller edge cases for complete coverage"""
    
    def test_controller_unsupported_file_type(self, tmp_path):
        """Test get_converter returns None for unsupported file type"""
        ui = FakeUI(tmp_path / "dummy.pdf")
        controller = ConverterController(ui)
        
        unsupported = tmp_path / "file.docx"
        result = controller.get_converter(unsupported)
        assert result is None
    
    def test_controller_null_converter_handling(self, tmp_path):
        """Test controller handles None converter gracefully"""
        test_file = tmp_path / "test.xyz"  # Unsupported extension
        test_file.write_text("content")
        
        class TestUI(FakeUI):
            def __init__(self, file):
                super().__init__(file)
            
            def get_user_input(self):
                return str(self._tmp), 1, "no_merge"
        
        ui = TestUI(test_file)
        controller = ConverterController(ui)
        # Should handle None converter without crashing
        controller.run()
    
    def test_controller_per_page_no_merge_complete(self, tmp_path, monkeypatch):
        """Test that per_page mode doesn't call show_merge_complete"""
        
        class MockConverter:
            def __init__(self, path):
                self.path = path
            
            def extract_content(self, progress_callback=None):
                return "content"
            
            def extract_content_per_item(self, progress_callback=None):
                if progress_callback:
                    progress_callback(1, 1)
                return ["page1", "page2"]
        
        class MockHandler:
            def save(self, content, destination):
                pass
            
            def save_multiple(self, contents, destination, source_name):
                pass
        
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")
        
        merge_called = []
        
        class TestUI(FakeUI):
            def __init__(self, file):
                super().__init__(file)
            
            def get_user_input(self):
                return str(test_file), 1, "per_page"
            
            def show_merge_complete(self, name):
                merge_called.append(name)
        
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.get_converter",
            lambda self, p: MockConverter(p)
        )
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.FORMAT_HANDLERS",
            {1: MockHandler(), 2: MockHandler(), 3: MockHandler()}
        )
        
        ui = TestUI(test_file)
        controller = ConverterController(ui)
        controller.run()
        
        # Merge complete should NOT be called in per_page mode
        assert len(merge_called) == 0
    
    def test_controller_merge_single_file(self, tmp_path, monkeypatch):
        """Test merge mode with single file creates _merged output"""
        
        class MockConverter:
            def __init__(self, path):
                self.path = path
            
            def extract_content(self, progress_callback=None):
                if progress_callback:
                    progress_callback(1, 1)
                return "test content"
            
            def extract_content_per_item(self, progress_callback=None):
                return ["page1"]
        
        class MockHandler:
            def save(self, content, destination):
                destination.with_suffix(".txt").write_text(content, encoding="utf-8")
            
            def save_multiple(self, contents, destination, source_name):
                pass
        
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        
        merge_complete_name = []
        
        class TestUI(FakeUI):
            def __init__(self, file):
                super().__init__(file)
            
            def get_user_input(self):
                return str(test_file), 1, "merge"
            
            def show_merge_complete(self, name):
                merge_complete_name.append(name)
        
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.get_converter",
            lambda self, p: MockConverter(p)
        )
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.FORMAT_HANDLERS",
            {1: MockHandler(), 2: MockHandler(), 3: MockHandler()}
        )
        
        ui = TestUI(test_file)
        controller = ConverterController(ui)
        controller.run()
        
        # Verify merged output was created
        assert len(merge_complete_name) == 1
        assert "merged" in merge_complete_name[0]
        
        merged_file = tmp_path / "document_merged.txt"
        assert merged_file.exists()


class TestControllerPerPageMode:
    """Test controller integration with per_page mode"""
    
    def test_controller_per_page_mode(self, tmp_path, monkeypatch):
        """Test that controller calls extract_content_per_item and save_multiple for per_page mode"""
        from controller.converter_controller import ConverterController
        
        # Track method calls
        extract_per_item_called = []
        save_multiple_called = []
        
        class MockConverter:
            def __init__(self, path):
                self.path = path
            
            def extract_content(self, progress_callback=None):
                return "merged content"
            
            def extract_content_per_item(self, progress_callback=None):
                extract_per_item_called.append(True)
                if progress_callback:
                    progress_callback(1, 1)
                return ["page1", "page2", "page3"]
        
        class MockHandler:
            def save(self, content, destination):
                pass
            
            def save_multiple(self, contents, destination, source_name):
                save_multiple_called.append((contents, destination, source_name))
        
        # Create test file
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")
        
        # Mock UI
        class TestUI:
            def draw_header(self):
                pass
            
            def clear_and_show_header(self):
                pass
            
            def get_user_input(self):
                return str(test_file), 1, "per_page"
            
            def select_files(self, file_data):
                return list(range(len(file_data)))
            
            def get_progress_bar(self):
                from contextlib import contextmanager
                @contextmanager
                def _ctx():
                    class FakeProg:
                        def add_task(self, *a, **kw):
                            return 1
                        def update(self, *a, **kw):
                            pass
                    yield FakeProg()
                return _ctx()
            
            def show_error(self, msg):
                pass
            
            def show_shutdown(self, elapsed):
                pass
            
            def show_conversion_summary(self, *a, **k):
                pass
        
        # Patch converter and handler
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.get_converter",
            lambda self, p: MockConverter(p)
        )
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.FORMAT_HANDLERS",
            {1: MockHandler(), 2: MockHandler(), 3: MockHandler()}
        )
        
        ui = TestUI()
        controller = ConverterController(ui)
        controller.run()
        
        # Verify per_page methods were called
        assert len(extract_per_item_called) == 1
        assert len(save_multiple_called) == 1
        
        # Verify save_multiple got the right data
        contents, dest, source = save_multiple_called[0]
        assert contents == ["page1", "page2", "page3"]
        assert dest == test_file
    
    def test_controller_progress_exception_handling(self, tmp_path, monkeypatch):
        """Test that controller gracefully handles exceptions in progress callback updates"""
        from controller.converter_controller import ConverterController
        
        test_file = tmp_path / "test.pdf"
        test_file.write_text("content")
        
        exception_raised = []
        
        class MockConverter:
            def __init__(self, path):
                self.path = path
            
            def extract_content(self, progress_callback=None):
                # Progress callback that will trigger exception in controller
                if progress_callback:
                    try:
                        # This will cause the exception in the controller's try-except
                        progress_callback(1, 1)
                    except:
                        # The controller catches and ignores it
                        exception_raised.append(True)
                return "test content"
        
        class TestUI:
            def __init__(self):
                self.update_count = 0
            
            def draw_header(self):
                pass
            
            def clear_and_show_header(self):
                pass
            
            def get_user_input(self):
                return str(test_file), 1, "no_merge"
            
            def select_files(self, file_data):
                return list(range(len(file_data)))
            
            def get_progress_bar(self):
                from contextlib import contextmanager
                @contextmanager
                def _ctx():
                    class ProgressTracker:
                        def __init__(self):
                            self.update_count = 0
                        
                        def add_task(self, *a, **kw):
                            return 1
                        
                        def update(self, *a, **kw):
                            self.update_count += 1
                            # Raise exception on second update to test exception handling
                            if self.update_count == 2:
                                raise RuntimeError("Progress update failed!")
                    
                    yield ProgressTracker()
                return _ctx()
            
            def show_error(self, msg):
                pass
            
            def show_shutdown(self, elapsed):
                pass
            
            def show_conversion_summary(self, *a, **k):
                pass
        
        from model.outputs import PlainTextHandler
        
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.get_converter",
            lambda self, p: MockConverter(p)
        )
        monkeypatch.setattr(
            "controller.converter_controller.ConverterController.FORMAT_HANDLERS",
            {1: PlainTextHandler(), 2: PlainTextHandler(), 3: PlainTextHandler()}
        )
        
        ui = TestUI()
        controller = ConverterController(ui)
        
        # Should not raise even though progress.update raises on second call
        controller.run()
        
        # Verify output was still created despite exception
        output_file = tmp_path / "test.txt"
        assert output_file.exists()
