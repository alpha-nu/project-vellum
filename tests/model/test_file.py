import os
from pathlib import Path
import pytest

from domain.model.file import File


def test_format_file_size_bytes():
    assert File.format_file_size(0) == "0B"
    assert File.format_file_size(512) == "512B"
    assert File.format_file_size(1500) == "1.5KB"
    assert File.format_file_size(2_500_000) == "2.4MB"
    assert File.format_file_size(5_000_000_000) == "4.7GB"
    assert File.format_file_size(3 * (1024 ** 4)) == "3.0TB"


def test_file_properties_and_to_dict():
    # Use the pure data constructor (no filesystem IO)
    f = File(name="sample.bin", size_bytes=2048)

    assert f.name == "sample.bin"
    # formatted size should reflect 2048 bytes -> 2.0KB
    assert f.formatted_size == "2.0KB"
    assert f.size_bytes == 2048

    d = f.to_dict()
    assert d["name"] == "sample.bin"
    assert d["size"] == "2.0KB"


def test_from_path_factory(monkeypatch):
    # Use monkeypatch to stub Path.stat and Path.name without touching disk
    class DummyStat:
        def __init__(self, st_size):
            self.st_size = st_size

    def fake_stat(self):
        return DummyStat(4096)

    # Patch pathlib.Path.stat to return our dummy stat
    monkeypatch.setattr("pathlib.Path.stat", fake_stat, raising=True)

    # Patch Path.name property to return a predictable filename
    import pathlib
    monkeypatch.setattr(pathlib.Path, "name", property(lambda self: "doc.pdf"), raising=False)

    f = File.from_path("/irrelevant/path")
    assert f.name == "doc.pdf"
    assert f.size_bytes == 4096
    assert f.formatted_size == "4.0KB"

