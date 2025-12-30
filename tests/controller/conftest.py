"""Shared fixtures and mock classes for controller tests."""

from contextlib import contextmanager
from unittest.mock import MagicMock
import pytest
from view.merge_mode import MergeMode
from view.output_format import OutputFormat
from view.interface import ActionResult


# ============================================================================
# Mock UI Builder
# ============================================================================

class MockUIBuilder:
    """Builder for creating mock UI objects with specific behaviors."""
    
    def __init__(self, file_path: str = "test.pdf"):
        self.file_path = file_path
        self.format_choice = OutputFormat.PLAIN_TEXT
        self.merge_mode = MergeMode.NO_MERGE
        self.merged_filename = None
        self.run_again = False
    
    def with_format(self, fmt):
        self.format_choice = fmt
        return self
    
    def with_merge_mode(self, mode):
        self.merge_mode = mode
        return self
    
    def with_merged_filename(self, name):
        self.merged_filename = name
        return self
    
    def with_run_again(self, should_run=True):
        self.run_again = should_run
        return self
    
    def build(self):
        """Build the mock UI object."""
        builder = self
        
        class TestUI:
            def __init__(self):
                self.update_count = 0
                self.show_error = MagicMock()
                self.show_conversion_summary = MagicMock()
                # ask_again returns True on first call (if configured), False thereafter
                from view.interface import ActionResult
                if builder.run_again:
                    side = [ActionResult.proceed(), ActionResult.terminate()]
                else:
                    side = [ActionResult.terminate()]
                self.ask_again = MagicMock(side_effect=side)
            
            def draw_header(self):
                pass
            
            
            def get_path_input(self):
                from view.interface import ActionResult
                return ActionResult.value(builder.file_path)

            def get_user_input(self):
                return builder.file_path, builder.format_choice, builder.merge_mode, builder.merged_filename
            
            def select_output_format(self):
                return ActionResult.value(builder.format_choice)

            def select_merge_mode(self):
                from view.interface import ActionResult
                return ActionResult.value(builder.merge_mode)

            def prompt_merged_filename(self):
                from view.interface import ActionResult
                return ActionResult.value(builder.merged_filename)
            
            def select_files(self, file_data):
                from view.interface import ActionResult
                return ActionResult.value(list(range(len(file_data))))
            
            def get_progress_bar(self):
                @contextmanager
                def _ctx():
                    class ProgressTracker:
                        def add_task(self, *a, **kw):
                            return 1
                        
                        def update(self, *a, **kw):
                            pass
                    
                    yield ProgressTracker()
                return _ctx()
        
        return TestUI()


# ============================================================================
# Mock Path Builder
# ============================================================================

class MockPathBuilder:
    """Builder for creating mock Path objects for testing without filesystem access."""
    
    def __init__(self, path_str: str = "/test/path"):
        self.path_str = path_str
        self._exists = True
        self._is_dir = False
        self._suffix = ".pdf"
        self._files = []
        self._stem = "test"
        self._stat_size = 1000
    
    def with_exists(self, exists: bool):
        self._exists = exists
        return self
    
    def with_is_dir(self, is_dir: bool):
        self._is_dir = is_dir
        return self
    
    def with_suffix(self, suffix: str):
        self._suffix = suffix
        return self
    
    def with_stem(self, stem: str):
        self._stem = stem
        return self
    
    def with_files(self, files: list):
        """Add child files for directory iteration."""
        self._files = files
        return self
    
    def with_stat_size(self, size: int):
        self._stat_size = size
        return self
    
    def build(self):
        """Build the mock Path object."""
        builder = self
        
        class MockStat:
            st_size = builder._stat_size
        
        class MockPath:
            def exists(self):
                return builder._exists
            
            def is_dir(self):
                return builder._is_dir
            
            @property
            def suffix(self):
                return builder._suffix
            
            @property
            def stem(self):
                return builder._stem
            
            @property
            def name(self):
                return f"{builder._stem}{builder._suffix}"
            
            def iterdir(self):
                """Iterate over child files/directories."""
                yield from builder._files
            
            def stat(self):
                return MockStat()
            
            def with_suffix(self, suffix: str):
                new_builder = MockPathBuilder(builder.path_str)
                new_builder._exists = builder._exists
                new_builder._is_dir = builder._is_dir
                new_builder._suffix = suffix
                new_builder._stem = builder._stem
                new_builder._files = builder._files
                new_builder._stat_size = builder._stat_size
                return new_builder.build()
            
            def with_name(self, name: str):
                # Parse name into stem and suffix
                if '.' in name:
                    stem, suffix = name.rsplit('.', 1)
                    suffix = '.' + suffix
                else:
                    stem, suffix = name, ''
                new_builder = MockPathBuilder(builder.path_str)
                new_builder._exists = builder._exists
                new_builder._is_dir = builder._is_dir
                new_builder._suffix = suffix
                new_builder._stem = stem
                new_builder._files = builder._files
                new_builder._stat_size = builder._stat_size
                return new_builder.build()
            
            def __truediv__(self, other: str):
                new_builder = MockPathBuilder(f"{builder.path_str}/{other}")
                new_builder._exists = True
                new_builder._is_dir = False
                new_builder._stem = other
                new_builder._suffix = ''
                return new_builder.build()
            
            def __str__(self):
                return builder.path_str
            
            def __fspath__(self):
                """Support os.fspath() and Path() conversion."""
                return builder.path_str
        
        return MockPath()
    
    def build_factory(self):
        """Build a factory function that returns this mock path."""
        mock_path = self.build()
        return lambda path_str: mock_path


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_converter():
    """Returns a converter factory that creates MagicMock converters."""
    def converter_factory(path, *args, **kwargs):
        mock = MagicMock()
        mock.path = path
        mock.extract_content = MagicMock(return_value="dummy")
        mock.extract_content_per_item = MagicMock(return_value=["page1", "page2", "page3"])
        return mock
    return converter_factory


@pytest.fixture
def mock_handler():
    """Returns a MagicMock handler instance."""
    mock = MagicMock()
    mock.save = MagicMock(return_value=5)
    mock.save_multiple = MagicMock(return_value=100)
    return mock


@pytest.fixture
def mock_converters(mock_converter):
    """Provide mock converters dictionary."""
    return {'.pdf': mock_converter, '.epub': mock_converter}


@pytest.fixture
def mock_pdf_path():
    """Provide a path factory that returns a standard mock PDF path."""
    mock_path = MockPathBuilder().with_suffix(".pdf").with_stem("test").build()
    return lambda s: mock_path


