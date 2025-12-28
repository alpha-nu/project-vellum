import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
)
from rich.live import Live
from contextlib import contextmanager
from rich.table import Table
from rich.align import Align
from typing import Optional
from enum import Enum
from view.interface import UIInterface
from view.keyboard import KeyboardKey


class MergeMode(Enum):
    NO_MERGE = "no_merge"
    MERGE = "merge"
    PER_PAGE = "per_page"
    
    @property
    def display_name(self) -> str:
        return {
            MergeMode.NO_MERGE: "no merge",
            MergeMode.MERGE: "merge",
            MergeMode.PER_PAGE: "file per page"
        }[self]
    
    @property
    def display_hint(self) -> str:
        return {
            MergeMode.NO_MERGE: "(separate file per document)",
            MergeMode.MERGE: "(combine all into single file)",
            MergeMode.PER_PAGE: "(one file per page/chapter)"
        }[self]


class OutputFormat(Enum):
    PLAIN_TEXT = "txt"
    MARKDOWN = "md"
    JSON = "json"
    
    @property
    def extension(self) -> str:
        return f".{self.value}"
    
    @property
    def display_name(self) -> str:
        return {
            OutputFormat.PLAIN_TEXT: "plain text",
            OutputFormat.MARKDOWN: "markdown",
            OutputFormat.JSON: "json"
        }[self]
    
    @property
    def display_hint(self) -> str:
        return f"({self.extension})"


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
        _StyledTimeMixin.__init__(self, style, "elapsed", time_provider=time_provider)
    
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
    def __init__(self, console: Optional[Console] = None, max_width: int = 120, colors: Optional[dict] = None, keyboard_reader=None):
        super().__init__(keyboard_reader=keyboard_reader)
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

    def print_center(self, renderable):
        """Print a renderable centered within the configured console width."""
        term_width = self.console.size.width
        self.console.print(Align.center(renderable, width=term_width))

    def input_center(self, prompt_symbol=">>: "):
        term_width = self.console.size.width
        panel_width = min(self.max_width, term_width)

        left_padding = (term_width - panel_width) // 2
        prompt_str = " " * left_padding + prompt_symbol
        markup = f"[{self.colors['primary']}]" + prompt_str + "[/]"
        return self.console.input(markup, markup=True)



    def clear_and_show_header(self):
        """Clear screen and display header - used after file selection to show clean progress view"""
        self.console.clear()
        self.draw_header()

    def draw_header(self):
        self.VERSION = "[ epub | pdf -> txt: converter ] v.1.0.0"
        ascii_logo = """
    ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
    ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
    ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
    ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
     ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
      ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
        """
        subtitle = f"{self.VERSION}"
        logo_width = max(len(line) for line in ascii_logo.splitlines())
        subtitle_width = len(subtitle) - 1
        padding = (logo_width - subtitle_width) // 2

        self.print_center(
            Panel(
                Align.center(
                    Text(ascii_logo, style=self.colors["logo"]) + Text(
                        "\n" + " " * padding + subtitle.lower(),
                        style=f"{self.colors['primary']}",
                    )
                ),
                border_style=self.colors["subtle"],
                width=min(self.max_width, self.console.size.width),
            )
        )

    def select_files(self, file_data: list[dict]) -> list[int]:
        """Display file selector and return indices of selected files.
        
        Args:
            file_data: List of dicts with 'name' and 'size' keys
            
        Returns:
            List of selected file indices
        """
        selected_indices = []
        current_index = 0
        while True:
            self.console.clear()
            self.draw_header()

            panel_width = min(self.max_width, self.console.size.width)
            table_width = panel_width - 4

            table = Table(
                show_header=False,
                width=table_width,
                show_edge=False,
            )
            table.add_column("file", style=self.colors["subtle"])

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

            self.print_center(
                Panel(
                    table,
                    padding=(1, 0, 0, 0),
                    title=f"[{self.colors['primary']}]\[select files for conversion][/]",
                    title_align="left",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )
            self.print_center(
                Panel(
                    f"[{self.colors['primary']}][{self.colors["secondary"]}]⬆︎ /⬇︎[/] :navigate  [{self.colors["secondary"]}][SPACE][/]:select  [{self.colors["secondary"]}][A][/]:all  [{self.colors["secondary"]}][ENTER][/]:confirm  [{self.colors["secondary"]}][Q][/]:quit[/]",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )

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
            elif token.key == KeyboardKey.CHAR and token.char == "a":
                if len(selected_indices) == len(file_data):
                    selected_indices = []
                else:
                    selected_indices = list(range(len(file_data)))
            elif token.key == KeyboardKey.CHAR and token.char == "q":
                import sys
                sys.exit(0)

        return selected_indices

    def get_user_input(self):
        """Get user input from user with selection dialogs."""
        path_str = self._get_path_input()
        format_choice = self._select_output_format()
        merge_choice = self._select_merge_mode()
        merged_filename = self._prompt_merged_filename() if merge_choice == MergeMode.MERGE else None
        return path_str, format_choice, merge_choice, merged_filename

    def _get_path_input(self) -> str:
        """Get path input from user."""
        self.console.clear()
        self.draw_header()

        path_prompt = Panel(
            f"[{self.colors['primary']}]provide a file or directory path[/] [{self.colors['secondary']}](e.g. source.pdf or /data)[/]",
            border_style=self.colors["subtle"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(path_prompt)
        path_str = self.input_center()
        return path_str

    def _select_output_format(self) -> OutputFormat:
        """
        Interactive output format selection menu with radio button options.
        
        Returns:
            Selected OutputFormat enum value
        """
        options = [
            OutputFormat.PLAIN_TEXT,
            OutputFormat.MARKDOWN,
            OutputFormat.JSON,
        ]
        current_index = 0  # Default to plain text
        
        while True:
            self.console.clear()
            self.draw_header()

            panel_width = min(self.max_width, self.console.size.width)
            table_width = panel_width - 4

            table = Table(
                show_header=False,
                width=table_width,
                show_edge=False,
            )
            table.add_column("option", style=self.colors["subtle"])

            for i, fmt in enumerate(options):
                # Radio button: filled if selected, empty if not
                if i == current_index:
                    radio = f"[{self.colors['secondary']}]●[/]"
                    option_text = f"[{self.colors['secondary']}]{fmt.display_name}[/] [{self.colors['secondary']}]{fmt.display_hint}[/]"
                else:
                    radio = "○"
                    option_text = f"[{self.colors['primary']}]{fmt.display_name}[/] {fmt.display_hint}"
                marker = f"[{self.colors['secondary']}]►[/]" if i == current_index else " "
                table.add_row(f"{marker} {radio} {option_text}")

            self.print_center(
                Panel(
                    table,
                    padding=(1, 0, 0, 0),
                    title=f"[{self.colors['primary']}]\[select output format][/]",
                    title_align="left",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )
            self.print_center(
                Panel(
                    f"[{self.colors['primary']}][{self.colors['secondary']}]⬆︎ /⬇︎[/] :navigate  [{self.colors['secondary']}][ENTER][/]:confirm[/]",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )

            token = self.keyboard_reader()

            if token.key == KeyboardKey.UP:
                current_index = (current_index - 1) % len(options)
            elif token.key == KeyboardKey.DOWN:
                current_index = (current_index + 1) % len(options)
            elif token.key == KeyboardKey.ENTER:
                # Enter confirms the current selection
                return options[current_index]

    def _select_merge_mode(self) -> MergeMode:
        """
        Interactive merge mode selection menu with radio button options.
        
        Returns:
            One of: MergeMode.NO_MERGE, MergeMode.MERGE, MergeMode.PER_PAGE
        """
        options = [
            MergeMode.NO_MERGE,
            MergeMode.MERGE,
            MergeMode.PER_PAGE,
        ]
        current_index = 0  # Default to "no_merge"
        
        while True:
            self.console.clear()
            self.draw_header()

            panel_width = min(self.max_width, self.console.size.width)
            table_width = panel_width - 4

            table = Table(
                show_header=False,
                width=table_width,
                show_edge=False,
            )
            table.add_column("option", style=self.colors["subtle"])

            for i, mode in enumerate(options):
                # Radio button: filled if selected, empty if not
                if i == current_index:
                    radio = f"[{self.colors['secondary']}]●[/]"
                    option_text = f"[{self.colors['secondary']}]{mode.display_name}[/] [{self.colors['secondary']}]{mode.display_hint}[/]"
                else:
                    radio = "○"
                    option_text = f"[{self.colors['primary']}]{mode.display_name}[/] {mode.display_hint}"
                marker = f"[{self.colors['secondary']}]►[/]" if i == current_index else " "
                table.add_row(f"{marker} {radio} {option_text}")

            self.print_center(
                Panel(
                    table,
                    padding=(1, 0, 0, 0),
                    title=f"[{self.colors['primary']}]\[select merge mode][/]",
                    title_align="left",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )
            self.print_center(
                Panel(
                    f"[{self.colors['primary']}][{self.colors['secondary']}]⬆︎ /⬇︎[/] :navigate  [{self.colors['secondary']}][ENTER][/]:confirm[/]",
                    border_style=self.colors["subtle"],
                    width=panel_width,
                )
            )

            token = self.keyboard_reader()

            if token.key == KeyboardKey.UP:
                current_index = (current_index - 1) % len(options)
            elif token.key == KeyboardKey.DOWN:
                current_index = (current_index + 1) % len(options)
            elif token.key == KeyboardKey.ENTER:
                # Enter confirms the current selection
                return options[current_index]

    def _prompt_merged_filename(self) -> str:
        """
        Prompt user for the name of the merged output file.
        
        Returns:
            The filename entered by the user
        """
        self.console.clear()
        self.draw_header()

        panel_width = min(self.max_width, self.console.size.width)
        prompt_panel = Panel(
            f"[{self.colors['primary']}]enter name for merged output file[/] [{self.colors['secondary']}](without extension)[/]",
            border_style=self.colors["subtle"],
            width=panel_width,
        )
        self.print_center(prompt_panel)
        filename = self.input_center()
        return filename.strip()

    def get_progress_bar(self):
        @contextmanager
        def _progress_ctx():
            progress = Progress(
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

            panel = Panel(
                progress,
                border_style=self.colors["subtle"],
                width=min(self.max_width, self.console.size.width),
            )
            term_width = self.console.size.width
            centered = Align.center(panel, width=term_width)
            with Live(centered, console=self.console, refresh_per_second=10):
                try:
                    yield progress
                finally:
                    pass

        return _progress_ctx()

    def print_panel(self, content: str, content_color_key: str = "primary"):
        panel = Panel(
            f"[{self.colors[content_color_key]}]{content}[/]",
            border_style=self.colors["subtle"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(panel)

    def show_error(self, message: str):
        self.print_panel(message, content_color_key="error")

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
        # Format runtime
        runtime_str = f"{total_runtime:.2f}s"
        
        # Determine output description based on merge mode
        if merge_mode == MergeMode.MERGE:
            output_desc = f"1 merged file"
            if merged_filename:
                output_desc += f" ({merged_filename})"
        elif merge_mode == MergeMode.PER_PAGE:
            output_desc = f"{output_count} pages/chapters"
        else:  # no_merge
            if single_output_filename:
                output_desc = single_output_filename
            else:
                output_desc = f"{output_count} files"
        
        content = (
            f"[{self.colors['primary']}]files processed:{'':<4}[/] [{self.colors['secondary']}]{total_files}[/]\n"
            f"[{self.colors['primary']}]output created:{'':<5}[/] [{self.colors['secondary']}]{output_desc}[/]\n"
            f"[{self.colors['primary']}]input size:{'':<9}[/] [{self.colors['secondary']}]{total_input_size_formatted}[/]\n"
            f"[{self.colors['primary']}]output size:{'':<8}[/] [{self.colors['secondary']}]{total_output_size_formatted}[/]\n\n"
            f"[{self.colors['accented']}]total runtime:{'':<6} {runtime_str}[/]\n"
        )
        
        panel = Panel(
            Text.from_markup(content),
            padding=(1, 0, 0, 0),
            title=f"[{self.colors['confirm']}]\[conversion complete][/]",
            title_align="left",
            border_style=self.colors["subtle"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(panel)

        # After showing the summary, provide simple actions for the user
        actions_hint = (
            f"[{self.colors['primary']}][{self.colors['secondary']}]"
            f"[ENTER][/]:run another conversion  [{self.colors['secondary']}][Q][/]:quit"
        )
        self.print_center(
            Panel(
                actions_hint,
                border_style=self.colors["subtle"],
                width=min(self.max_width, self.console.size.width),
            )
        )

    def ask_again(self):
        while True:
            token = self.keyboard_reader()
            if token.key == KeyboardKey.ENTER:
                return True
            elif token.key == KeyboardKey.CHAR and token.char == "q":
                return False
            # Else continue waiting
