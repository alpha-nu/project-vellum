import os
from pathlib import Path
from interface import RetroCLI
from converters import PDFConverter, EPubConverter
from outputs import PlainTextHandler, MarkdownHandler, JSONHandler
from rich.panel import Panel
from rich.align import Align

def get_converter(file_path: Path):
    ext_map = {".pdf": PDFConverter, ".epub": EPubConverter}
    ext = file_path.suffix.lower()
    return ext_map.get(ext)(file_path) if ext in ext_map else None

def main():
    ui = RetroCLI()
    ui.draw_header()
    
    input_str, format_choice, merge_enabled = ui.get_user_input()
    input_path = Path(input_str)
    
    if not input_path.exists():
        error_panel = Align.center(Panel(
            "[bold red]FATAL ERROR: PATH NOT FOUND[/bold red]",
            border_style="grey74",
            width=min(ui.max_width, ui.console.size.width)
        ))
        ui.console.print(error_panel)
        return

    # Batch logic
    if input_path.is_dir():
        all_compatible_files = [f for f in input_path.iterdir() if f.suffix.lower() in [".pdf", ".epub"]]
        files = ui.select_files(all_compatible_files)
    else:
        files = [input_path]
    
    if not files:
        no_files_panel = Align.center(Panel(
            "[bold yellow]NO COMPATIBLE FILES FOUND[/bold yellow]",
            border_style="grey74",
            width=min(ui.max_width, ui.console.size.width)
        ))
        ui.console.print(no_files_panel)
        return

    handler = {1: PlainTextHandler(), 2: MarkdownHandler(), 3: JSONHandler()}[format_choice]
    accumulator = []

    with ui.get_progress_bar() as progress:
        task = progress.add_task("[green]Processing...", total=len(files))
        
        for file in files:
            progress.update(task, description=f"[white]Converting {file.name}...[/white]")
            converter = get_converter(file)
            if converter:
                content = converter.extract_content()
                if merge_enabled:
                    accumulator.append(f"\n--- START SOURCE: {file.name} ---\n{content}")
                else:
                    handler.save(content, file)
                ui.console.print(f"  [green]✔[/green] {file.name}")
            progress.advance(task)

    if merge_enabled and accumulator:
        output_name = input_path / "VELLUM_MERGED_OUTPUT" if input_path.is_dir() else input_path.with_name(f"{input_path.stem}_merged")
        handler.save("\n\n".join(accumulator), output_name)
        merge_complete_panel = Align.center(Panel(
            f"[bold plum3]MERGE COMPLETE[/bold plum3]\n[grey74]{output_name.name}[/grey74]",
            border_style="grey74",
            width=min(ui.max_width, ui.console.size.width)
        ))
        ui.console.print(merge_complete_panel)

    shutdown_panel = Align.center(Panel(
        "[bold plum3]SHUTDOWN COMPLETE[/bold plum3]",
        border_style="grey74",
        width=min(ui.max_width, ui.console.size.width)
    ))
    ui.console.print(shutdown_panel)

if __name__ == "__main__":
    main()