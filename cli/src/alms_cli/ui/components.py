"""Rich UI components for beautiful terminal output."""

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich import box
from pathlib import Path

console = Console()


def print_header(title: str, subtitle: str = ""):
    """Print a beautiful header panel."""
    content = f"[bold white]{title}[/bold white]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    
    console.print()
    console.print(
        Panel(
            content,
            box=box.ROUNDED,
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def print_step(step_num: int, total: int, message: str):
    """Print a step indicator."""
    console.print(f"[bold blue]Step {step_num}/{total}:[/bold blue] {message}")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] [green]{message}[/green]")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[bold red]✗[/bold red] [red]{message}[/red]")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[bold blue]ℹ[/bold blue] [blue]{message}[/blue]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] [yellow]{message}[/yellow]")


def create_progress():
    """Create a beautiful progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )


def print_tree(directory: Path, prefix: str = ""):
    """Print a beautiful directory tree."""
    tree = Tree(
        f"[bold blue]{directory.name}[/bold blue]",
        guide_style="blue",
    )
    
    def add_to_tree(path: Path, parent: Tree):
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        for item in items:
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            
            if item.is_dir():
                branch = parent.add(
                    f"[bold blue]{item.name}/[/bold blue]",
                    guide_style="blue",
                )
                add_to_tree(item, branch)
            else:
                parent.add(
                    f"[dim]{item.name}[/dim]",
                    guide_style="dim",
                )
    
    add_to_tree(directory, tree)
    console.print(tree)


def print_project_summary(project_path: Path, files_created: int, features: list[str]):
    """Print a beautiful project summary panel."""
    table = Table(
        box=box.ROUNDED,
        border_style="green",
        title="[bold green]Project Created Successfully![/bold green]",
    )
    
    table.add_column("Property", style="bold blue")
    table.add_column("Value", style="white")
    
    table.add_row("Name", project_path.name)
    table.add_row("Location", str(project_path))
    table.add_row("Files Created", str(files_created))
    table.add_row("Features", ", ".join(features))
    
    console.print()
    console.print(table)
    console.print()
    
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  [dim]cd[/dim] [cyan]{project_path.name}[/cyan]")
    console.print(f"  [dim]uv sync[/dim]")
    console.print(f"  [dim]uv run -m src.api.main[/dim]")
    console.print()
