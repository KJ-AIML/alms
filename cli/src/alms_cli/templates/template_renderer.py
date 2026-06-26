"""Small Jinja2 renderer for generated project templates."""

from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
)


class TemplateRenderError(RuntimeError):
    """Raised when a template cannot be loaded or rendered."""


class TemplateRenderer:
    """Render packaged template files into generated project files."""

    def __init__(self, template_root: Path | None = None):
        self.template_root = template_root or Path(__file__).parent / "files"
        self.environment = Environment(
            loader=FileSystemLoader(str(self.template_root)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            newline_sequence="\n",
        )

    def template_names(self) -> list[str]:
        """Return all packaged template names."""
        return sorted(self.environment.list_templates(extensions=["j2"]))

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template by package-relative path."""
        try:
            template = self.environment.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound as exc:
            raise TemplateRenderError(f"Template not found: {template_name}") from exc
        except TemplateError as exc:
            raise TemplateRenderError(
                f"Failed to render {template_name}: {exc}"
            ) from exc

    def render_to_path(
        self,
        template_name: str,
        destination: Path,
        context: dict[str, Any],
    ) -> None:
        """Render a template and write it to a destination path."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            self.render(template_name, context),
            encoding="utf-8",
            newline="\n",
        )
