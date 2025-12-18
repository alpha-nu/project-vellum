from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

class RetroCLI:
    def __init__(self):
        self.console = Console()
        self.colors = {"fg": "green3", "accent": "bright_magenta"}

    def draw_header(self):
        ascii_logo = """
        ██╗   ██╗███████╗██╗     ██╗     ██╗   ██╗███╗   ███╗
        ██║   ██║██╔════╝██║     ██║     ██║   ██║████╗ ████║
        ██║   ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║
        ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║
         ╚████╔╝ ███████╗███████╗███████╗╚██████╔╝██║ ╚═╝ ██║
          ╚═══╝  ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
        [ epub | pdf -> txt: CONVERTER ]
        """
        self.console.print(Panel(Text(ascii_logo, style=self.colors["fg"]), border_style=self.colors["accent"]))

    def get_user_input(self):
        self.console.print("\n[bold cyan]PROMPT:[/bold cyan] Provide a File or Directory path (e.g., /data)")
        path_str = Prompt.ask("[bold green]>>[/bold green]")
        
        self.console.print("\n[yellow][1] PLAIN TEXT\n[2] MARKDOWN\n[3] JSON[/yellow]")
        format_choice = IntPrompt.ask("[bold green]>> SELECT FORMAT[/bold green]", choices=["1", "2", "3"], show_choices=False)
        
        merge_choice = Confirm.ask("[bold yellow]>> MERGE_BATCH_INTO_SINGLE_FILE?[/bold yellow]", default=False)
            
        return path_str, format_choice, merge_choice

    def get_progress_bar(self):
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )