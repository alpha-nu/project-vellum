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
import readchar
from pathlib import Path
from typing import Optional
from view.interface import UIInterface


class _StyledTimeMixin:
    def __init__(self, style: str, attr: str):
        super().__init__()
        self._style = style
        self._attr = attr

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
    def __init__(self, style: str):
        _StyledTimeMixin.__init__(self, style, "elapsed")
    
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
                import time
                elapsed = time.perf_counter() - start_time
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
            return Text.from_markup(f"[{self.colors['progress']}]{percentage}[/]")


class StyledDescriptionColumn(TextColumn):
    def __init__(self, colors: dict):
        super().__init__("[progress.description]{task.description}")
        self.colors = colors

    def render(self, task):
        fields = getattr(task, "fields", {}) or {}
        status = fields.get("status", "pending")
        filename = fields.get("filename", "")

        if status == "converting":
            return Text.from_markup(f"[italic {self.colors['progress']}]converting {filename}[/]")
        elif status == "done":
            return Text.from_markup(f"[{self.colors['confirm']}]✓ {filename}[/]")
        else:
            return Text.from_markup(f"[{self.colors['border']}]{filename}[/]")


class RetroCLI(UIInterface):
    def __init__(self, console: Optional[Console] = None, max_width: int = 120, colors: Optional[dict] = None):
        self.max_width = max_width
        self.console = console or Console()
        # color scheme (hex values for consistency)
        default_colors = {
            "border": "#9aa0a6",  # soft grey for borders
            "prompt": "#e9d8ff",  # softest purple for prompts
            "logo": "#c25a1a",  # lavender for logo
            "error": "#ff6b81",  # rosy for errors
            "confirm": "#52d9d8",  # green for confirmations
            "progress": "#c9a961",  # soft blue for progress indicators,
            "options": "#7dd9d8", # soft cyan for output options
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
        markup = f"[{self.colors['prompt']}]" + prompt_str + "[/]"
        return self.console.input(markup, markup=True)

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
                        style=f"{self.colors['prompt']}",
                    )
                ),
                border_style=self.colors["border"],
                width=min(self.max_width, self.console.size.width),
            )
        )

    def select_files(self, files: list[Path]) -> list[Path]:
        selected_files = []
        current_index = 0
        while True:
            self.console.clear()
            self.draw_header()

            panel_width = min(self.max_width, self.console.size.width)
            table_width = panel_width - 4

            table = Table(
                title=f"[{self.colors['prompt']}]select files for conversion[/]",
                show_header=False,
                width=table_width,
                border_style=self.colors["border"],
            )
            table.add_column("file", style=self.colors["border"])

            for i, file in enumerate(files):
                checkbox = f"[{self.colors['options']}]✔[/]" if file in selected_files else f"[{self.colors['options']}]❏[/]"
                marker = f"[{self.colors['options']}]►[/]" if i == current_index else " "
                if i == current_index:
                    filename_text = f"[{self.colors['options']}]" + file.name + "[/]"
                else:
                    filename_text = file.name
                table.add_row(f"{marker} {checkbox} {filename_text}")

            self.print_center(
                Panel(
                    table,
                    border_style=self.colors["border"],
                    width=panel_width,
                )
            )
            self.print_center(
                Panel(
                    f"[{self.colors['prompt']}][{self.colors["options"]}]⬆︎ /⬇︎[/] :navigate  [{self.colors["options"]}][SPACE][/]:toggle  [{self.colors["options"]}][ENTER][/]:confirm[/]",
                    border_style=self.colors["border"],
                    width=panel_width,
                )
            )

            key = readchar.readchar()

            if key == "\x1b":
                next1 = readchar.readchar()
                next2 = readchar.readchar()
                if next1 == "[":
                    if next2 == "A":
                        current_index = (current_index - 1) % len(files)
                    elif next2 == "B":
                        current_index = (current_index + 1) % len(files)
            elif key == " ":
                file = files[current_index]
                if file in selected_files:
                    selected_files.remove(file)
                else:
                    selected_files.append(file)
            elif key in ("\r", "\n"):
                break
            elif key.lower() == "a":
                selected_files = list(files)
                break
            elif key.lower() == "q":
                break

        return selected_files

    def get_user_input(self):
        self.console.clear()
        self.draw_header()

        path_prompt = Panel(
            f"[{self.colors['prompt']}]provide a file or directory path[/] [{self.colors['options']}](e.g. source.pdf or /data)[/]",
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(path_prompt)
        path_str = self.input_center()

        format_prompt = Panel(
            (f"[{self.colors['prompt']}]select output format[/]\n\n"
             f"[{self.colors['border']}][1][/] [{self.colors["options"]}]plain text[/]\n"
             f"[{self.colors['border']}][2][/] [{self.colors["options"]}]markdown[/]\n"
             f"[{self.colors['border']}][3][/] [{self.colors["options"]}]json[/]"),
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(format_prompt)
        while True:
            resp = self.input_center()
            if resp and resp.strip() in ("1", "2", "3"):
                format_choice = int(resp.strip())
                break
            self.print_center(
                Panel(
                    f"[{self.colors['error']}]please enter 1, 2, or 3[/]",
                    border_style=self.colors["border"],
                    width=min(self.max_width, self.console.size.width),
                )
            )

        merge_prompt = Panel(
            f"[{self.colors['prompt']}]merge batch into single file [{self.colors['options']}](y/[bold]N[/])[/]?",
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(merge_prompt)
        while True:
            resp = self.input_center()
            if not resp:
                merge_choice = False
                break
            r = resp.strip().lower()
            if r in ("y", "yes"):
                merge_choice = True
                break
            if r in ("n", "no"):
                merge_choice = False
                break
            self.print_center(
                Panel(
                    f"[{self.colors['error']}]please answer y or n[/]",
                    border_style=self.colors["border"],
                    width=min(self.max_width, self.console.size.width),
                )
            )

        return path_str, format_choice, merge_choice

    def get_progress_bar(self):
        @contextmanager
        def _progress_ctx():
            progress = Progress(
                StyledDescriptionColumn(self.colors),
                BarColumn(
                    bar_width=None,
                    style=self.colors["border"],
                    complete_style=self.colors["progress"],
                    finished_style=self.colors["border"],
                ),
                StyledPercentageColumn(self.colors),
                StyledTimeElapsedColumn(self.colors["progress"]),
                console=self.console,
                transient=True,
            )

            panel = Panel(
                progress,
                border_style=self.colors["border"],
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

    def print_panel(self, content: str, content_color_key: str = "prompt"):
        panel = Panel(
            f"[{self.colors[content_color_key]}]{content}[/]",
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(panel)

    def show_error(self, message: str):
        self.print_panel(message, content_color_key="error")

    def show_no_files(self):
        self.print_panel("no compatible files found", content_color_key="error")

    def show_merge_complete(self, output_name: str):
        content = (
            f"[{self.colors['confirm']}]merge complete[/]\n"
            f"[{self.colors['confirm']}] {output_name} [/]")
        panel = Panel(
            Align.center(Text.from_markup(content)),
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(panel)

    def show_shutdown(self, elapsed_seconds: float):
        content = (
            f"[{self.colors['confirm']}]conversion complete[/]\n"
            f"[{self.colors['progress']}]run time: {elapsed_seconds:.2f}s[/]")
        panel = Panel(
            Text.from_markup(content),
            border_style=self.colors["border"],
            width=min(self.max_width, self.console.size.width),
        )
        self.print_center(panel)
