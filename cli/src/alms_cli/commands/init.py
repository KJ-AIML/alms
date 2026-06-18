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
from alms_cli.templates import (
    TemplateGenerator,
    PROFILE_CAPABILITIES,
    resolve_capabilities,
)

console = Console()

custom_style = Style([
    ("qmark", "fg:#FFFFFF"),
    ("question", "fg:#FFFFFF nobold"),
    ("answer", "fg:#FFFFFF"),
    ("pointer", "fg:#22C55E nobold"),
    ("highlighted", "fg:#FFFFFF nobold"),
    ("selected", "fg:#FFFFFF nobold"),
    ("separator", "fg:#666666"),
    ("instruction", "fg:#888888"),
    ("text", "fg:#FFFFFF nobold"),
    ("disabled", "fg:#666666 italic"),
    ("checkbox", "fg:#666666 nobold"),
    ("checkbox.selected", "fg:#22C55E nobold"),
])

VALID_PROFILES = list(PROFILE_CAPABILITIES.keys())


def init_command(
    name: str = typer.Argument(None, help="Project name"),
    path: str = typer.Option(None, "--path", "-p", help="Path to create project"),
    profile: str = typer.Option(
        "core-api",
        "--profile",
        help=f"Project profile: {', '.join(VALID_PROFILES)}",
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i", help="Interactive mode"
    ),
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

    # Resolve profile
    if profile not in PROFILE_CAPABILITIES:
        print_error(f"Unknown profile: {profile}. Valid: {', '.join(VALID_PROFILES)}")
        raise typer.Exit(1)

    capabilities = resolve_capabilities(profile=profile)

    # Interactive feature selection (only when no profile or "core-api" selected)
    features: list[str] = []
    if interactive and profile == "core-api":
        feature_choices = [
            ("Database (PostgreSQL)", False),
            ("Redis Cache", False),
            ("AI Agents (LangChain)", False),
            ("Observability (OpenTelemetry)", False),
            ("Docker Support", False),
            ("CI/CD (GitHub Actions)", False),
        ]

        selected = questionary.checkbox(
            "Add capabilities to core-api:",
            choices=[
                questionary.Choice(title=fn, checked=de)
                for fn, de in feature_choices
            ],
            style=custom_style,
            instruction="(Use arrow keys to move, <space> to select)",
        ).ask()

        if selected:
            features = selected
            # Merge feature selections into capabilities
            capabilities = resolve_capabilities(profile="core-api", features=features)

    display_profile = profile if not features else f"{profile}+custom"

    console.print()
    print_step(1, 4, f"Creating project structure in {project_path}")
    print_info(f"Profile: {display_profile}")

    with create_progress() as progress:
        task = progress.add_task("Generating files...", total=100)

        generator = TemplateGenerator(name, project_path)
        files_created = generator.generate(capabilities)

        progress.update(task, completed=100)

    print_success(f"Created {files_created} files")
    console.print()

    print_step(2, 4, "Setting up configuration")
    print_success("Environment template created (.env.example)")
    print_success("Git ignore created (.gitignore)")
    if "docker" in capabilities:
        print_success("Docker configuration created")
    console.print()

    print_step(3, 4, "Initializing project structure")
    print_success("API layer created")
    print_success("Execution layer created")
    if "llm" in capabilities:
        print_success("Agent layer created")
    if "database" in capabilities:
        print_success("Database layer created")
    if "observability" in capabilities:
        print_success("Observability layer created")
    console.print()

    print_step(4, 4, "Finalizing setup")
    print_success("Tests scaffolded")
    print_success("Documentation created")
    if "ci" in capabilities:
        print_success("GitHub workflows configured")
    console.print()

    print_project_summary(
        project_path,
        files_created,
        sorted(capabilities),
    )

    console.print(
        Panel(
            "[bold green]Your ALMS project is ready![/bold green]\n\n"
            "[dim]Run the commands above to get started[/dim]",
            box=box.ROUNDED,
            border_style="green",
        )
    )
    console.print()