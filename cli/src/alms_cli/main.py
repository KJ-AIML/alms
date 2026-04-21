"""Main CLI application entry point."""

import typer
from typer import Typer
from rich.console import Console
from alms_cli import __version__
from alms_cli.commands.init import init_command
from alms_cli.commands.info import info_app

app = Typer(
    name="alms",
    help="ALMS CLI - Beautiful project scaffolding tool",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

app.command(name="init")(init_command)
app.add_typer(info_app, name="info")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """ALMS CLI - AI-First Backend Project Scaffolding"""
    if ctx.invoked_subcommand:
        return
    
    console.print()
    console.print("[bold blue]╔══════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║[/bold blue] [bold white]ALMS CLI[/bold white]                          [bold blue]║[/bold blue]")
    console.print("[bold blue]║[/bold blue] [dim]AI-First Backend Project Scaffolding[/dim]  [bold blue]║[/bold blue]")
    console.print("[bold blue]╚══════════════════════════════════════════╝[/bold blue]")
    console.print()
    console.print(f"[dim]Version: {__version__}[/dim]")
    console.print()
    console.print("[bold]Commands:[/bold]")
    console.print("  [green]init[/green]     Create a new ALMS project")
    console.print("  [green]info[/green]     Show project information")
    console.print()
    console.print("[dim]Run 'alms <command> --help' for more information[/dim]")
    console.print()
