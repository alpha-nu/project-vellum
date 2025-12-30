from unittest.mock import Mock

from domain.adapters.file_factories import file_from_path


def test_from_path_factory_with_mock_path():
    # Create a mock path-like object with .name and .stat().st_size
    mock_path = Mock()
    mock_path.name = "doc.pdf"
    mock_stat = Mock()
    mock_stat.st_size = 4096
    mock_path.stat.return_value = mock_stat

    f = file_from_path(mock_path)
    assert f.name == "doc.pdf"
    assert f.size_bytes == 4096
    assert f.formatted_size == "4.0KB"
