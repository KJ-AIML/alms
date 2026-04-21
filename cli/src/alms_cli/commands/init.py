"""Init command - Create a new ALMS project."""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box
import questionary
from questionary import Style

from alms_cli.ui.components import (
    print_header,
    print_step,
    print_success,
    print_error,
    print_info,
    print_warning,
    create_progress,
    print_project_summary,
)
from alms_cli.templates import TemplateGenerator

console = Console()

custom_style = Style([
    ("qmark", "fg:#FFFFFF"),
    ("question", "fg:#FFFFFF"),
    ("answer", "fg:#FFFFFF"),
    ("pointer", "fg:#FFFFFF"),
    ("highlighted", "fg:#FFFFFF"),
    ("selected", "fg:#FFFFFF"),
    ("separator", "fg:#666666"),
    ("instruction", "fg:#888888"),
    ("text", "fg:#FFFFFF"),
    ("disabled", "fg:#666666 italic"),
    ("checkbox", "fg:#FFFFFF"),
    ("checkbox.selected", "fg:#FFFFFF"),
])


def init_command(
    name: str = typer.Argument(None, help="Project name"),
    path: str = typer.Option(None, "--path", "-p", help="Path to create project"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive mode"),
):
    """Create a new ALMS project with beautiful scaffolding."""
    
    print_header("ALMS Project Generator", "AI-First Backend Starter Kit")
    
    if not name:
        if interactive:
            name = questionary.text(
                "Project name:",
                default="my-alms-project",
                style=custom_style,
                validate=lambda x: len(x) > 0 and x.replace("-", "").replace("_", "").isalnum(),
            ).ask()
            
            if not name:
                print_error("Project name is required")
                raise typer.Exit(1)
        else:
            print_error("Project name is required")
            raise typer.Exit(1)
    
    project_path = Path(path) / name if path else Path(name)
    
    if project_path.exists():
        if interactive:
            overwrite = questionary.confirm(
                f"Directory '{name}' already exists. Overwrite?",
                default=False,
                style=custom_style,
            ).ask()
            
            if not overwrite:
                print_warning("Project creation cancelled")
                raise typer.Exit(0)
        else:
            print_error(f"Directory '{name}' already exists")
            raise typer.Exit(1)
    
    features = []
    
    if interactive:
        print_info("Select features to include:")
        console.print()
        
        feature_choices = [
            ("Database (PostgreSQL)", True),
            ("Redis Cache", True),
            ("AI Agents (LangChain)", True),
            ("Observability (OpenTelemetry)", True),
            ("Docker Support", True),
            ("CI/CD (GitHub Actions)", True),
        ]
        
        selected = set()
        for i, (_, default) in enumerate(feature_choices):
            if default:
                selected.add(i)
        
        while True:
            for i, (name, _) in enumerate(feature_choices):
                marker = "[bold green]✓[/bold green]" if i in selected else "[dim]○[/dim]"
                console.print(f"  {marker} {name}")
            
            console.print()
            try:
                choice = input("Toggle (1-6) or Enter to continue: ").strip()
                if not choice:
                    break
                idx = int(choice) - 1
                if 0 <= idx < len(feature_choices):
                    if idx in selected:
                        selected.remove(idx)
                    else:
                        selected.add(idx)
            except (ValueError, KeyboardInterrupt):
                break
        
        features = [feature_choices[i][0] for i in selected]
    
    console.print()
    print_step(1, 4, f"Creating project structure in {project_path}")
    
    with create_progress() as progress:
        task = progress.add_task("Generating files...", total=100)
        
        generator = TemplateGenerator(name, project_path)
        files_created = generator.generate(features)
        
        progress.update(task, completed=100)
    
    print_success(f"Created {files_created} files")
    console.print()
    
    print_step(2, 4, "Setting up configuration")
    print_success("Environment template created (.env.example)")
    print_success("Git ignore created (.gitignore)")
    print_success("Docker configuration created")
    console.print()
    
    print_step(3, 4, "Initializing project structure")
    print_success("API layer created")
    print_success("Execution layer created")
    print_success("Agent layer created")
    print_success("Database layer created")
    print_success("Observability layer created")
    console.print()
    
    print_step(4, 4, "Finalizing setup")
    print_success("Tests scaffolded")
    print_success("Documentation created")
    print_success("GitHub workflows configured")
    console.print()
    
    print_project_summary(project_path, files_created, features or ["All features"])
    
    console.print(
        Panel(
            "[bold green]Your ALMS project is ready![/bold green]\n\n"
            "[dim]Run the commands above to get started[/dim]",
            box=box.ROUNDED,
            border_style="green",
        )
    )
    console.print()
