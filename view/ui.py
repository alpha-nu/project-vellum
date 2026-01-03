import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
    SpinnerColumn
)
from rich.live import Live
from contextlib import contextmanager
from rich.table import Table
from rich.align import Align
from typing import Optional
from dataclasses import dataclass
from view.output_format import OutputFormat
from view.merge_mode import MergeMode
from view.interface import UIInterface, ActionResult
from view.keyboard import KeyboardKey
from controller.workflow.state_machine import WorkflowState
from sys import stdout
from rich.box import HEAVY_HEAD, Box, MINIMAL

HORIZONTALS_NO_BOTTOM = Box(
    " ── \n"
    "    \n"
    " ── \n"
    "    \n"
    " ── \n"
    " ── \n"
    "    \n"
    "    \n"
)

# Breadcrumb is now a simple list of strings representing the path from the
# workflow state stack. Legacy `BreadcrumbState` dataclass was removed.

class _StyledTimeMixin:
    def __init__(self, style: str, attr: str, time_provider=time.perf_counter):
        super().__init__()
        self._style = style
        self._attr = attr
        self._time_provider = time_provider

    def render(self, task):
        value = getattr(task, self._attr)
        if value is None:
            return Text("00:00", style=self._style)
        return Text(self._format_time(value), style=self._style)

    @staticmethod
    def _format_time(seconds: float) -> str:
        secs = int(seconds)
        hours, remainder = divmod(secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

class StyledTimeElapsedColumn(_StyledTimeMixin, TimeRemainingColumn):
    def __init__(self, style: str, time_provider=None):
        _StyledTimeMixin.__init__(self, style, "elapsed", time_provider=time_provider or time.perf_counter)
    
    def render(self, task):
        fields = getattr(task, "fields", {}) or {}
        status = fields.get("status", "pending")
        
        # When done, show final conversion time
        if status == "done":
            conversion_time = fields.get("conversion_time")
            if conversion_time is None:
                return Text("00:00", style=self._style)
            return Text(f"{self._format_time(conversion_time)}", style=self._style)
        
        # While converting, calculate elapsed from start_time
        if status == "converting":
            start_time = fields.get("start_time")
            if start_time is not None:
                elapsed = self._time_provider() - start_time
                return Text(f"{self._format_time(elapsed)}", style=self._style)
        
        # Pending or no start time
        return Text("00:00", style=self._style)

class StyledPercentageColumn(TextColumn):
    def __init__(self, colors: dict):
        super().__init__("{task.percentage:>3.0f}%")
        self.colors = colors

    def render(self, task):
        fields = getattr(task, "fields", {}) or {}
        status = fields.get("status", "pending")
        percentage = f"{task.percentage:>3.0f}%"

        if status == "done":
            return Text.from_markup(f"[{self.colors['confirm']}]{percentage}[/]")
        else:
            return Text.from_markup(f"[{self.colors['accented']}]{percentage}[/]")

class StyledDescriptionColumn(TextColumn):
    def __init__(self, colors: dict):
        super().__init__("[progress.description]{task.description}")
        self.colors = colors

    def render(self, task):
        fields = getattr(task, "fields", {}) or {}
        status = fields.get("status", "pending")
        filename = fields.get("filename", "")

        if status == "converting":
            return Text.from_markup(f"[italic {self.colors['accented']}]converting {filename}[/]")
        elif status == "done":
            return Text.from_markup(f"[{self.colors['confirm']}]✓ {filename}[/]")
        else:
            return Text.from_markup(f"[{self.colors['subtle']}]{filename}[/]")

class RetroCLI(UIInterface):
    VERSION = "1.0.0"
    
    def __init__(self, console: Optional[Console] = None, max_width: int = 120, colors: Optional[dict] = None, keyboard_reader=None):
        self._keyboard_reader = keyboard_reader
        self.max_width = max_width
        self.console = console or Console()
        default_colors = {
            "logo": "#c25a1a",       # Orange/rust for the ASCII logo
            "primary": "#e9d8ff",    # Soft purple for primary text and prompts
            "secondary": "#52d9d8",  # Teal for interactive options and highlights
            "subtle": "#9aa0a6",     # Soft grey for borders and subtle UI elements
            "accented": "#c9a961",   # Gold for progress indicators and emphasis
            "confirm": "#6fc67c",    # Light green for confirmations and success
            "error": "#ff6b81",      # Rosy red for error messages
        }
        self.colors = {**default_colors, **(colors or {})}
        
        # Breadcrumb state (updated by controller on state transitions)
        self.breadcrumb = []

    @property
    def keyboard_reader(self):
        return self._keyboard_reader

    @property
    def panel_width(self) -> int:
        """Compute constrained panel width based on terminal and max width."""
        return min(self.max_width, self.console.size.width)

    def _create_panel(self, content, title: Optional[str] = None, padding: Optional[tuple] = None, title_color: Optional[str] = "primary", **style_args) -> Panel:
        """Create a styled panel with consistent settings."""
        kwargs = {
            "border_style": self.colors["subtle"],
            "width": self.panel_width,
            "box": HORIZONTALS_NO_BOTTOM,
        }
        if title:
            kwargs["title"] = f"[{self.colors[title_color]}]\\[{title}][/ ]"
            kwargs["title_align"] = "left"
        if padding:
            kwargs["padding"] = padding
        return Panel(content, **(kwargs | style_args))

    def _create_hint_panel(self, hints: str) -> Panel:
        """Create a panel for keyboard navigation hints."""
        return Panel(
            f"[{self.colors['primary']}]{hints}[/]",
            border_style=f"dim {self.colors["subtle"]}",
            width=self.panel_width,
            box=HEAVY_HEAD,
        )

    def _create_selection_table(self) -> Table:
        """Create a pre-configured table for selection menus."""
        table = Table(
            show_header=False,
            width=self.panel_width - 4,
            show_edge=False,
        )
        table.add_column("option", style=self.colors["subtle"])
        return table

    def _render_radio_row(self, is_current: bool, display_name: str, hint: str) -> str:
        """Render a radio button row for selection menus."""
        if is_current:
            marker = f"[{self.colors['secondary']}]►[/]"
            radio = f"[{self.colors['secondary']}]●[/]"
            text = f"[{self.colors['secondary']}]{display_name}[/] [{self.colors['secondary']}]{hint}[/]"
        else:
            marker = " "
            radio = "○"
            text = f"[{self.colors['primary']}]{display_name}[/] {hint}"
        return f"{marker} {radio} {text}"

    def _radio_select(self, options: list, title: str) -> ActionResult:
        """Generic radio-button selection menu.
        
        Args:
            options: List of enum values with display_name and display_hint properties
            title: Panel title text
            
        Returns:
            Selected option from the list
        """
        current_index = 0
        hints = f"[{self.colors['secondary']}]⬆︎ /⬇︎[/] :navigate  [{self.colors['secondary']}][ENTER][/]:confirm  [{self.colors['secondary']}][BACKSPACE][/]:back  [{self.colors['secondary']}][Q][/]:quit"
        
        while True:
            self.clear_and_show_header()
            table = self._create_selection_table()
            for i, option in enumerate(options):
                table.add_row(self._render_radio_row(
                    i == current_index, 
                    option.display_name, 
                    option.display_hint
                ))

            self.print_center(self._create_panel(table, title=title, padding=(1, 0, 1, 0)))
            self.print_center(self._create_hint_panel(hints))

            token = self.keyboard_reader()

            if token.key == KeyboardKey.BACKSPACE:
                return ActionResult.back()

            if token.key == KeyboardKey.CHAR and token.char == "q":
                return ActionResult.terminate()

            if token.key == KeyboardKey.UP:
                current_index = (current_index - 1) % len(options)
            elif token.key == KeyboardKey.DOWN:
                current_index = (current_index + 1) % len(options)
            elif token.key == KeyboardKey.ENTER:
                return ActionResult.value(options[current_index])

    def print_center(self, renderable):
        """Print a renderable centered within the configured console width."""
        term_width = self.console.size.width
        self.console.print(Align.center(renderable, width=term_width))

    def input_center(self, prompt_symbol=">>", title = "", hint = ""):
        left_padding = (self.console.size.width - self.panel_width) // 2 + 3
        markup = (
            f"[{self.colors['subtle']}]{hint}[/]\n\n"
            f"[{self.colors['primary']}]{prompt_symbol}[/]"
            )
        self.print_center(self._create_panel(Text.from_markup(markup), title, padding=(1, 0, 0, 1)))

        hints = f"[{self.colors['secondary']}][ENTER][/]:confirm  [{self.colors['secondary']}][\Q][/]:quit"
        self.print_center(self._create_hint_panel(hints))
        
        # Some Magic to hijack and reposition the blinking cursos
        stdout.write("\033[5A") # More Magic: move up 6 lines. The hight of the hints panel + padding
        stdout.write(f"\033[{len(prompt_symbol) + left_padding}C") # move left
        stdout.flush()
        user_input = input("") 
        stdout.write("\033[5B") # Move Down 5 (past bottom border), not to override the above
        stdout.flush()
        return user_input


    def clear_and_show_header(self):
        """Clear screen and display header with breadcrumb navigation."""
        self.console.clear()
        self.draw_header()
        self.draw_breadcrumb()

    def draw_breadcrumb(self) -> None:
        breadcrumb_text = Text()
        last_index = len(self.breadcrumb) - 1
        for i, label in enumerate(self.breadcrumb):
            if i > 0:
                breadcrumb_text.append(" >> ", style=self.colors["subtle"])
            color = self.colors["secondary"] if i == last_index else self.colors["primary"]
            breadcrumb_text.append(Text.from_markup(f"[{color}]{label}[/]"))

        self.print_center(self._create_panel(breadcrumb_text, padding=(0, 0, 0, 0), box=MINIMAL))

    def draw_header(self):
        ascii_logo = """
    ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
    ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
    ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
    ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
     ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
      ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
        """
        subtitle = f"[ epub | pdf -> txt ]"
        logo_width = max(len(line) for line in ascii_logo.splitlines())
        subtitle_width = len(subtitle) - 1
        padding = (logo_width - subtitle_width) // 2

        self.print_center(
            Panel(
                Align.center(
                    Text(ascii_logo, style=self.colors["logo"]) + 
                    Text("\n" + " ".ljust(padding) + subtitle.lower(), style=f"{self.colors['accented']}")
                ),
                border_style=f"dim {self.colors["subtle"]}",
                width=self.panel_width,
                box=HEAVY_HEAD,
                subtitle=f"[not dim {self.colors['subtle']}]{self.VERSION}[/]",
                subtitle_align="right",
            )
        )

    def select_files(self, file_data: list[dict]) -> ActionResult[list[int]]:
        """Display file selector and return indices of selected files.
        
        Args:
            file_data: List of dicts with 'name' and 'size' keys
            
        Returns:
            List of selected file indices
        """
        selected_indices = []
        current_index = 0
        hints = f"[{self.colors['secondary']}]⬆︎ /⬇︎[/] :navigate  [{self.colors['secondary']}][SPACE][/]:select  [{self.colors['secondary']}][A][/]:all  [{self.colors['secondary']}][ENTER][/]:confirm  [{self.colors['secondary']}][BACKSPACE][/]:back  [{self.colors['secondary']}][Q][/]:quit"
        
        while True:
            self.clear_and_show_header()
            table = self._create_selection_table()
            
            for i, file_info in enumerate(file_data):
                checkbox = "✔" if i in selected_indices else "❏"
                marker = f"[{self.colors['secondary']}]►[/]" if i == current_index else " "
                
                if i == current_index:
                    checkbox_colored = f"[{self.colors['secondary']}]{checkbox}[/]"
                    filename_text = f"[{self.colors['secondary']}]{file_info['name']}[/]"
                    size_text = f"[{self.colors['secondary']}]({file_info['size']})[/]"
                else:
                    checkbox_colored = checkbox
                    filename_text = f"[{self.colors['primary']}]{file_info['name']}[/]"
                    size_text = f"[{self.colors['subtle']}]({file_info['size']})[/]"
                table.add_row(f"{marker} {checkbox_colored} {filename_text} {size_text}")

            self.print_center(self._create_panel(table, title="select files for conversion", padding=(1, 0, 1, 0)))
            self.print_center(self._create_hint_panel(hints))

            token = self.keyboard_reader()

            if token.key == KeyboardKey.UP:
                current_index = (current_index - 1) % len(file_data)
            elif token.key == KeyboardKey.DOWN:
                current_index = (current_index + 1) % len(file_data)
            elif token.key == KeyboardKey.SPACE:
                if current_index in selected_indices:
                    selected_indices.remove(current_index)
                else:
                    selected_indices.append(current_index)
            elif token.key == KeyboardKey.ENTER:
                break
            elif token.key == KeyboardKey.BACKSPACE:
                return ActionResult.back()
            elif token.key == KeyboardKey.CHAR and token.char == "a":
                if len(selected_indices) == len(file_data):
                    selected_indices = []
                else:
                    selected_indices = list(range(len(file_data)))
            elif token.key == KeyboardKey.CHAR and token.char == "q":
                return ActionResult.terminate()

        self.clear_and_show_header()

        return ActionResult.value(selected_indices)

    def get_path_input(self) -> ActionResult[str]:
        """Get path input from user."""
        self.clear_and_show_header()
        
        result = self.input_center(title="select input source", hint="e.g. source.pdf or /data")
        if result.strip().lower() == "\\q":
            return ActionResult.terminate()
        return ActionResult.value(result)

    def select_output_format(self) -> ActionResult[OutputFormat]:
        """Interactive output format selection menu."""
        return self._radio_select(
            [OutputFormat.PLAIN_TEXT, OutputFormat.MARKDOWN, OutputFormat.JSON],
            title="select output format"
        )

    def select_merge_mode(self) -> ActionResult[MergeMode]:
        """Interactive merge mode selection menu."""
        return self._radio_select(
            [MergeMode.NO_MERGE, MergeMode.MERGE, MergeMode.PER_PAGE],
            title="select merge mode"
        )

    def prompt_merged_filename(self) -> ActionResult[str]:
        """Prompt user for the name of the merged output file."""
        self.clear_and_show_header()
        
        result = self.input_center(title="select merged output", hint="output file name without extension")
        if result.strip().lower() == "\\q":
            return ActionResult.terminate()
        return ActionResult.value(result.strip())

    def get_progress_bar(self):
        self.clear_and_show_header()
        @contextmanager
        def _progress_ctx():
            progress = Progress(
                SpinnerColumn(
                    speed=.75,
                    style=self.colors["accented"]
                ),
                StyledDescriptionColumn(self.colors),
                BarColumn(
                    bar_width=None,
                    style=self.colors["subtle"],
                    complete_style=self.colors["accented"],
                    finished_style=self.colors["subtle"],
                ),
                StyledPercentageColumn(self.colors),
                StyledTimeElapsedColumn(self.colors["accented"]),
                console=self.console,
                transient=True,
            )

            panel = self._create_panel(progress, title="selected files", padding=(1, 0, 1, 0))
            term_width = self.console.size.width
            centered = Align.center(panel, width=term_width)
            with Live(centered, console=self.console, refresh_per_second=10):
                yield progress

        return _progress_ctx()

    def show_error(self, message: str):
        markup = f"[{self.colors['error']}]" + message + "[/]"
        term_width = self.console.size.width
        left_padding = (term_width - self.panel_width) // 2 + 1
        self.console.print(" " * left_padding + markup, markup=True)

    def show_conversion_summary(
        self, 
        total_files: int, 
        output_count: int, 
        merge_mode: MergeMode, 
        merged_filename: Optional[str], 
        total_runtime: float, 
        total_input_size_formatted: str,
        total_output_size_formatted: str,
        single_output_filename: Optional[str] = None
    ):
        """Display comprehensive conversion summary and completion message."""
        runtime_str = f"{total_runtime:.2f}s"
        
        # Determine output description based on merge mode
        if merge_mode == MergeMode.MERGE:
            output_desc = f"1 merged file"
            if merged_filename:
                output_desc += f" ({merged_filename})"
        elif merge_mode == MergeMode.PER_PAGE:
            output_desc = f"{output_count} pages/chapters"
        else:  # no_merge
            output_desc = single_output_filename if single_output_filename else f"{output_count} files"
        
        content = (
            f"[{self.colors['primary']}]files processed:{'':<4}[/] [{self.colors['secondary']}]{total_files}[/]\n"
            f"[{self.colors['primary']}]output created:{'':<5}[/] [{self.colors['secondary']}]{output_desc}[/]\n"
            f"[{self.colors['primary']}]input size:{'':<9}[/] [{self.colors['secondary']}]{total_input_size_formatted}[/]\n"
            f"[{self.colors['primary']}]output size:{'':<8}[/] [{self.colors['secondary']}]{total_output_size_formatted}[/]\n\n"
            f"[{self.colors['accented']}]total runtime:{'':<6} {runtime_str}[/]"
        )
        
        self.print_center(self._create_panel(
            Text.from_markup(content), 
            title="conversion complete", 
            padding=(1, 0, 1, 1),
        ))

    def ask_again(self) -> ActionResult[bool]:
        hints = f"[{self.colors['secondary']}][ENTER][/]:try again  [{self.colors['secondary']}][Q][/]:quit"
        self.print_center(self._create_hint_panel(hints))
        while True:
            token = self.keyboard_reader()
            if token.key == KeyboardKey.ENTER:
                return ActionResult.proceed()
            elif token.key == KeyboardKey.CHAR and token.char == "q":
                return ActionResult.terminate()
            # Else continue waiting

