"""Core controller integration tests."""

from controller.converter_controller import ConverterController
from tests.controller.conftest import MockUIBuilder, MockConverter, MockPathBuilder


def test_directory_batch_processing(mock_converters, mock_handlers):
    """Test controller can get compatible files."""
    
    ui = MockUIBuilder("mock_dir").build()
    mock_path_factory = lambda path_str: None  # Not used in this test
    controller = ConverterController(ui, mock_converters, mock_handlers, mock_path_factory)
    
    mock_path = (
        MockPathBuilder("/mock_dir")
        .with_is_dir(True)
        .with_files([
            MockPathBuilder("/mock_dir/file1.pdf").with_suffix(".pdf").with_stem("file1").build(),
            MockPathBuilder("/mock_dir/file2.epub").with_suffix(".epub").with_stem("file2").build(),
            MockPathBuilder("/mock_dir/file3.txt").with_suffix(".txt").with_stem("file3").build(),
        ])
        .build()
    )
    
    compatible = controller._get_compatible_files(mock_path)
    
    assert {f.name for f in compatible} == {"file1.pdf", "file2.epub"}


