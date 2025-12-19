from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import os
from pathlib import Path

class RetroCLI:
    def __init__(self):
        self.console = Console()
        self.colors = {"fg": "lavender", "accent": "medium_purple4"}

    def draw_header(self):
        self.VERSION = "1.0.0"
        ascii_logo = """
        ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
        ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
        ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
        ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
         ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
          ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
        [ epub | pdf -> txt: CONVERTER ]
        """

        subtitle = f"[ {self.VERSION} ]"
        
        # Calculate padding to center the subtitle
        # Assuming ascii_logo's widest line is around 60-70 chars for centering purposes
        logo_width = max(len(line) for line in ascii_logo.splitlines())
        subtitle_width = len(subtitle) - 1 # account for rich's markup
        padding = (logo_width - subtitle_width) // 2
        
        self.console.print(
            Panel(
                Text(ascii_logo, style=self.colors["fg"])
                + Text("\n" + " " * padding + subtitle, style=f"bold {self.colors['accent']}"),
                border_style=self.colors["accent"],
                width=self.console.width # Fill the entire screen width
            )
        )

    def select_files(self, files: list[Path]) -> list[Path]:
        
        selected_files = []
        
        while True:
            table = Table(
                title="[bold yellow]SELECT FILES FOR CONVERSION[/bold yellow]",
                row_styles=["none", "dim"],
                show_header=True,
                header_style="bold magenta",
                width=self.console.width
            )
            table.add_column(" ", style="dim", width=3)
            table.add_column("Filename", style="green")
            
            for i, file in enumerate(files):
                checkbox = "[green]\[x][/green]" if file in selected_files else "[red]\[ ][/red]"
                table.add_row(str(i + 1), f"{checkbox} {file.name}")
            
            self.console.print(table)
            self.console.print("\\n[bold cyan]Select file numbers (e.g., 1 3 5), \'a\' to select all, or \'d\' to finish:[/bold cyan]")
            
            choice = Prompt.ask("[bold green]>>[/bold green]").lower()
            
            if choice == 'd':
                break
            elif choice == 'a':
                selected_files = list(files)
            else:
                try:
                    indices = [int(x) - 1 for x in choice.split()]
                    for i in indices:
                        if 0 <= i < len(files):
                            file = files[i]
                            if file in selected_files:
                                selected_files.remove(file)
                            else:
                                selected_files.append(file)
                except ValueError:
                    self.console.print("[red]Invalid input. Please enter numbers, \'a\', or \'d\'.[/red]")
            self.console.clear()
            self.draw_header()
        
        return selected_files

    def get_user_input(self):
        self.console.print("\\n[bold cyan]PROMPT:[/bold cyan] Provide a File or Directory path (e.g., /data)")
        path_str = Prompt.ask("[bold green]>>[/bold green]")
        
        self.console.print("\\n[yellow][1] PLAIN TEXT\\n[2] MARKDOWN\\n[3] JSON[/yellow]")
        format_choice = IntPrompt.ask("[bold green]>> SELECT FORMAT[/bold green]", choices=["1", "2", "3"], show_choices=False)
        
        merge_choice = Confirm.ask("[bold yellow]>> MERGE_BATCH_INTO_SINGLE_FILE?[/bold yellow]", default=False)
            
        return path_str, format_choice, merge_choice

    def get_progress_bar(self):
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )