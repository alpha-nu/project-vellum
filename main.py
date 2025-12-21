import os
from pathlib import Path
from view.ui import RetroCLI
from model.converters import PDFConverter, EPubConverter
from model.outputs import PlainTextHandler, MarkdownHandler, JSONHandler
import time

def get_converter(file_path: Path):
    ext_map = {".pdf": PDFConverter, ".epub": EPubConverter}
    ext = file_path.suffix.lower()
    return ext_map.get(ext)(file_path) if ext in ext_map else None

def main(ui=None):
    ui = ui or RetroCLI()
    ui.draw_header()
    
    input_str, format_choice, merge_enabled = ui.get_user_input()
    input_path = Path(input_str)
    
    if not input_path.exists():
        ui.show_error("fatal error: path not found")
        return

    # Batch logic
    if input_path.is_dir():
        all_compatible_files = [f for f in input_path.iterdir() if f.suffix.lower() in [".pdf", ".epub"]]
        files = ui.select_files(all_compatible_files)
    else:
        files = [input_path]
    
    if not files:
        ui.show_no_files()
        return

    handler = {1: PlainTextHandler(), 2: MarkdownHandler(), 3: JSONHandler()}[format_choice]
    accumulator = []

    start_time = time.perf_counter()
    with ui.get_progress_bar() as progress:
        # create a progress bar task per file (0-100). We'll mark each file 100 when done.
        tasks = {file: progress.add_task(f"{file.name}", total=100) for file in files}

        for file in files:
            task_id = tasks[file]
            progress.update(task_id, description=f"converting {file.name}...", completed=0)
            converter = get_converter(file)
            if converter:
                # provide a progress callback that updates the per-file task
                def _make_cb(tid, fname):
                    def _cb(current, total):
                        try:
                            pct = int((current / total) * 100) if total else 100
                            progress.update(tid, completed=pct, description=f"converting {fname}...")
                        except Exception:
                            pass
                    return _cb

                content = converter.extract_content(progress_callback=_make_cb(task_id, file.name))
                if merge_enabled:
                    accumulator.append(f"\n--- start source: {file.name} ---\n{content}")
                else:
                    handler.save(content, file)
                # mark file as completed
                progress.update(task_id, completed=100, description=f"done {file.name}")

    if merge_enabled and accumulator:
        output_name = input_path / "merged_output" if input_path.is_dir() else input_path.with_name(f"{input_path.stem}_merged")
        handler.save("\n\n".join(accumulator), output_name)
        ui.show_merge_complete(output_name.name)

    elapsed = time.perf_counter() - start_time
    ui.show_shutdown(elapsed)

if __name__ == "__main__":
    main()