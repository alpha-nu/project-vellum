import os
from pathlib import Path
import types

import main as main_module


class FakeUI:
    def __init__(self, tmp_file: Path):
        self._tmp = tmp_file

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

            def add_task(self, desc, total=100):
                tid = len(self.tasks) + 1
                self.tasks[tid] = {"desc": desc, "completed": 0}
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
    monkeypatch.setattr(main_module, "get_converter", lambda p: FakeConverter(p))

    ui = FakeUI(tmp_file)

    # run main with injected UI
    main_module.main(ui=ui)

    # verify output file was written by PlainTextHandler
    out = tmp_file.with_suffix('.txt')
    assert out.exists()
    assert out.read_text() == "dummy"
