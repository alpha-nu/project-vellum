from pathlib import Path
from model.core import BaseConverter


class FakeConverter(BaseConverter):
    def extract_content(self, progress_callback=None) -> str:
        total = 3
        texts = []
        for i in range(total):
            texts.append(f"page {i}")
            if progress_callback:
                progress_callback(i + 1, total)
        return "\n\n".join(texts)


def test_fake_converter_progress_called():
    calls = []

    def cb(current, total):
        calls.append((current, total))

    conv = FakeConverter(Path("dummy.pdf"))
    out = conv.extract_content(progress_callback=cb)

    assert "page 0" in out
    assert len(calls) == 3
    assert calls[0] == (1, 3)
