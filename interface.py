from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.live import Live
from contextlib import contextmanager
from rich.table import Table
from rich.align import Align
import readchar
from pathlib import Path

class RetroCLI:
    def __init__(self):
        self.max_width = 120  # 60% of typical terminal (200 chars)
        self.console = Console()
        self.colors = {"fg": "plum3", "accent": "grey74"}

    def print_center(self, renderable):
        """Print a renderable centered within the configured console width."""
        term_width = self.console.size.width
        self.console.print(Align.center(renderable, width=term_width))

    def input_center(self, prompt_symbol='>>: '):
        """Show a left-justified prompt within the centered max-width layout.

        The prompt_symbol appears at the left edge of the max-width panel,
        which is itself centered on the terminal.
        """
        term_width = self.console.size.width
        panel_width = min(self.max_width, term_width)

        # Left-justify the prompt with left padding to align with the centered panel
        left_padding = (term_width - panel_width) // 2
        prompt_str = " " * left_padding + prompt_symbol

        # Render with markup for color
        markup = f"[bold grey74]{prompt_str}[/bold grey74]"
        return self.console.input(markup, markup=True)


    def draw_header(self):
        self.VERSION = "[ epub | pdf -> txt: CONVERTER ] v.1.0.0"
        ascii_logo = """
    ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
    ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
    ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
    ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
     ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
      ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
        """
        subtitle = f"{self.VERSION}"
        
        # Calculate padding to center the subtitle
        # Assuming ascii_logo's widest line is around 60-70 chars for centering purposes
        logo_width = max(len(line) for line in ascii_logo.splitlines())
        subtitle_width = len(subtitle) - 1 # account for rich's markup
        padding = (logo_width - subtitle_width) // 2
        
        self.print_center(
                Panel(
                Align.center(Text(ascii_logo, style=self.colors["fg"]) + Text("\n" + " " * padding + subtitle, style=f"bold {self.colors['accent']}")),
                border_style=self.colors["accent"],
                width=min(self.max_width, self.console.size.width),
            )
        )

    def select_files(self, files: list[Path]) -> list[Path]:
        """File selection using arrow keys and Enter. Header stays visible."""
        
        selected_files = []
        current_index = 0
        
        while True:
            self.console.clear()
            self.draw_header()
            
            # Build table with highlighted current selection
            table = Table(
                title="[bold plum3]SELECT FILES FOR CONVERSION[/bold plum3]",
                show_header=False,
                    width=min(self.max_width, self.console.size.width),
                border_style=self.colors["accent"]
            )
            table.add_column("File", style="grey74")
            
            for i, file in enumerate(files):
                checkbox = "[plum3]✓[/plum3]" if file in selected_files else "[plum3]◯[/plum3]"
                style = "bold plum3" if i == current_index else ""
                marker = "→" if i == current_index else " "
                filename_text = f"[{style}]{file.name}[/{style}]" if style else file.name
                table.add_row(
                    f"{marker} {checkbox} {filename_text}"
                )
            
            # Center the table
            self.print_center(Panel(table, border_style=self.colors["accent"], width=min(self.max_width, self.console.size.width)))
            self.print_center(Panel("[bold plum3]↑/↓ Navigate  SPACE Toggle  ENTER Confirm[/bold plum3]", border_style=self.colors["accent"], width=min(self.max_width, self.console.size.width)))
            
            key = readchar.readchar()
            
            if key == '\x1b':  # Escape sequence
                next1 = readchar.readchar()
                next2 = readchar.readchar()
                if next1 == '[':
                    if next2 == 'A':  # Up arrow
                        current_index = (current_index - 1) % len(files)
                    elif next2 == 'B':  # Down arrow
                        current_index = (current_index + 1) % len(files)
            elif key == ' ':  # Space to toggle
                file = files[current_index]
                if file in selected_files:
                    selected_files.remove(file)
                else:
                    selected_files.append(file)
            elif key in ('\r', '\n'):  # Enter to confirm
                break
            elif key.lower() == 'a':  # 'a' to select all
                selected_files = list(files)
                break
            elif key.lower() == 'q':  # 'q' to quit/go back
                break
        
        return selected_files

    def get_user_input(self):
        self.console.clear()
        self.draw_header()
        
        # Input path prompt
        path_prompt = Panel(
            "[bold plum3]Provide a File or Directory path[/bold plum3]\n[grey74](e.g., /data)[/grey74]",
            border_style=self.colors["accent"],
            width=min(self.max_width, self.console.size.width)
        )
        self.print_center(path_prompt)
        path_str = self.input_center()
        
        # Format selection prompt
        format_prompt = Panel(
            "[bold plum3]SELECT OUTPUT FORMAT[/bold plum3]\n\n[grey74][1][/grey74] PLAIN TEXT\n[grey74][2][/grey74] MARKDOWN\n[grey74][3][/grey74] JSON",
            border_style=self.colors["accent"],
            width=min(self.max_width, self.console.size.width)
        )
        self.print_center(format_prompt)
        # simple validation loop for numeric choice
        while True:
            resp = self.input_center()
            if resp and resp.strip() in ("1", "2", "3"):
                format_choice = int(resp.strip())
                break
            self.print_center(Panel("[bold yellow]Please enter 1, 2, or 3[/bold yellow]", border_style=self.colors['accent'], width=min(self.max_width, self.console.size.width)))
        
        # Merge confirmation prompt
        merge_prompt = Panel(
            "[bold plum3]Merge batch into single file?[/bold plum3]",
            border_style=self.colors["accent"],
            width=min(self.max_width, self.console.size.width)
        )
        self.print_center(merge_prompt)
        # yes/no prompt
        while True:
            resp = self.input_center()
            if not resp:
                merge_choice = False
                break
            r = resp.strip().lower()
            if r in ('y', 'yes'):
                merge_choice = True
                break
            if r in ('n', 'no'):
                merge_choice = False
                break
            self.print_center(Panel("[bold yellow]Please answer Y or N[/bold yellow]", border_style=self.colors['accent'], width=min(self.max_width, self.console.size.width)))
            
        return path_str, format_choice, merge_choice

    def get_progress_bar(self):
        # Return a context manager that renders the Progress inside a centered Panel
        @contextmanager
        def _progress_ctx():
            progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=None),
                TextColumn("{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
                transient=True,
            )

            panel = Panel(progress, border_style=self.colors["accent"], width=min(self.max_width, self.console.size.width))
            term_width = self.console.size.width
            centered = Align.center(panel, width=term_width)
            with Live(centered, console=self.console, refresh_per_second=10):
                try:
                    yield progress
                finally:
                    pass

        return _progress_ctx()