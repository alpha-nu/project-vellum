import os
from pathlib import Path
import pytest

from model.file import File


def test_format_file_size_bytes():
    assert File.format_file_size(0) == "0B"
    assert File.format_file_size(512) == "512B"
    assert File.format_file_size(1500) == "1.5KB"
    assert File.format_file_size(2_500_000) == "2.4MB"
    assert File.format_file_size(5_000_000_000) == "4.7GB"
    assert File.format_file_size(3 * (1024 ** 4)) == "3.0TB"

