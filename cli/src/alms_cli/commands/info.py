"""Info command - Show project information."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

from alms_cli.ui.components import print_tree, print_error, print_info
from alms_cli import __version__

info_app = typer.Typer(
    name="info",
    help="Show project information",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@info_app.command()
def project():
    """Show information about the current ALMS project."""

    project_root = Path.cwd()

    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        print_error("Not an ALMS project (pyproject.toml not found)")
        console.print()
        print_info("Run 'alms init <name>' to create a new project")
        console.print()
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel(
            f"[bold white]ALMS Project Info[/bold white]\n"
            f"[dim]CLI Version: {__version__}[/dim]",
            box=box.ROUNDED,
            border_style="blue",
        )
    )
    console.print()

    table = Table(
        box=box.ROUNDED,
        border_style="blue",
        title="[bold]Project Details[/bold]",
    )

    table.add_column("Property", style="bold blue")
    table.add_column("Value", style="white")

    table.add_row("Name", project_root.name)
    table.add_row("Location", str(project_root))
    table.add_row("Has pyproject.toml", "Yes")
    table.add_row("Has src/", str((project_root / "src").exists()))
    table.add_row("Has tests/", str((project_root / "src" / "tests").exists()))
    table.add_row("Has alembic/", str((project_root / "alembic").exists()))

    console.print(table)
    console.print()

    console.print("[bold]Project Structure:[/bold]")
    console.print()

    if (project_root / "src").exists():
        print_tree(project_root / "src")

    console.print()


@info_app.callback(invoke_without_command=True)
def info(ctx: typer.Context):
    """Show information about the current ALMS project."""
    if ctx.invoked_subcommand is None:
        project()
