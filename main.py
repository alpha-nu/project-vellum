import os
from pathlib import Path
from interface import RetroCLI
from converters import PDFConverter, EPubConverter
from outputs import PlainTextHandler, MarkdownHandler, JSONHandler

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
        ui.console.print("[red]FATAL ERROR: PATH_NOT_FOUND[/red]")
        return

    # Batch logic
    files = [f for f in input_path.iterdir() if f.suffix.lower() in [".pdf", ".epub"]] if input_path.is_dir() else [input_path]
    
    if not files:
        ui.console.print("[yellow]NO COMPATIBLE FILES FOUND.[/yellow]")
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
        ui.console.print(f"\n[bold bright_green]MERGE COMPLETE: {output_name.name}[/bold bright_green]")

    ui.console.print("\n[bold green]SHUTDOWN COMPLETE.[/bold green]")

if __name__ == "__main__":
    main()