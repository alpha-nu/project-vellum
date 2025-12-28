"""Shared fixtures and mock classes for controller tests."""

from contextlib import contextmanager
import pytest
from view.ui import MergeMode, OutputFormat


# ============================================================================
# Mock Converters
# ============================================================================

class MockConverter:
    """Base mock converter for testing."""
    
    def __init__(self, path, content="dummy"):
        self.path = path
        self.content = content
    
    def extract_content(self, progress_callback=None):
        if progress_callback:
            progress_callback(1, 1)
        return self.content
    
    def extract_content_per_item(self, progress_callback=None):
        if progress_callback:
            progress_callback(1, 1)
        return ["page1", "page2", "page3"]


# ============================================================================
# Mock Handlers
# ============================================================================

class MockHandler:
    """Base mock output handler that captures saves in memory."""
    
    def __init__(self):
        self.saved_files = {}  # Track what was saved: {path: content}
    
    def save(self, content, destination):
        """Capture save without writing to disk."""
        self.saved_files[destination] = content
        # Return mock size
        return len(content) if content else 0
    
    def save_multiple(self, contents, destination, source_name):
        """Mock save_multiple that tracks pages in memory."""
        self.saved_files[destination] = contents
        return 100  # Mock size
    
    def get_saved_content(self, destination):
        """Helper to retrieve what was saved."""
        return self.saved_files.get(destination)


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
        self.selected_indices = None
        self.errors = []
        self.summaries = []
        self.progress_exception_on_update = None
    
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
    
    def with_selected_indices(self, indices):
        self.selected_indices = indices
        return self
    
    def with_progress_exception_on_update(self, update_count):
        self.progress_exception_on_update = update_count
        return self
    
    def build(self):
        """Build the mock UI object."""
        builder = self
        
        class TestUI:
            def __init__(self):
                self.ask_calls = 0
                self.update_count = 0
            
            def draw_header(self):
                pass
            
            def clear_and_show_header(self):
                pass
            
            def get_user_input(self):
                return builder.file_path, builder.format_choice, builder.merge_mode, builder.merged_filename
            
            def select_files(self, file_data):
                if builder.selected_indices is not None:
                    return builder.selected_indices
                return list(range(len(file_data)))  # Select all by default
            
            def get_progress_bar(self):
                @contextmanager
                def _ctx():
                    class ProgressTracker:
                        def add_task(self, *a, **kw):
                            return 1
                        
                        def update(self, *a, **kw):
                            self.update_count += 1
                            if builder.progress_exception_on_update == self.update_count:
                                raise RuntimeError("Progress update failed!")
                    
                    tracker = ProgressTracker()
                    tracker.update_count = 0
                    yield tracker
                return _ctx()
            
            def show_error(self, msg):
                builder.errors.append(msg)
            
            def show_conversion_summary(self, *a, **k):
                builder.summaries.append(k)
            
            def ask_again(self):
                self.ask_calls += 1
                return builder.run_again if self.ask_calls == 1 else False
        
        return TestUI()


# ============================================================================
# Mock Path Builder
# ============================================================================

class MockPathBuilder:
    """Builder for creating mock Path objects for testing without filesystem access."""
    
    def __init__(self, path_str: str = "/test/path"):
        self.path_str = path_str
        self._is_dir = False
        self._suffix = ".pdf"
        self._files = []
        self._stem = "test"
    
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
    
    def build(self):
        """Build the mock Path object."""
        builder = self
        
        class MockPath:
            def is_dir(self):
                return builder._is_dir
            
            @property
            def suffix(self):
                return builder._suffix
            
            @property
            def name(self):
                return f"{builder._stem}{builder._suffix}"
            
            def iterdir(self):
                """Iterate over child files/directories."""
                yield from builder._files
        
        return MockPath()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_converters():
    """Provide mock converters dictionary for isolated unit tests."""
    return {'.pdf': MockConverter, '.epub': MockConverter}


@pytest.fixture
def mock_handlers():
    """Provide mock handlers dictionary for isolated unit tests."""
    return {OutputFormat.PLAIN_TEXT: MockHandler}


