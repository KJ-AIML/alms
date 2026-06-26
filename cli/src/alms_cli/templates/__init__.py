"""Project template generator -- capability-aware edition."""

from .profiles import (
    ALL_CAPABILITIES,
    CAPABILITY_TO_EXTRA,
    FEATURE_LABEL_TO_CAPABILITY,
    NO_EXTRA_CAPABILITIES,
    PROFILE_CAPABILITIES,
    resolve_capabilities,
    resolve_extras,
)

__all__ = [
    "ALL_CAPABILITIES",
    "CAPABILITY_TO_EXTRA",
    "FEATURE_LABEL_TO_CAPABILITY",
    "NO_EXTRA_CAPABILITIES",
    "PROFILE_CAPABILITIES",
    "TemplateGenerator",
    "resolve_capabilities",
    "resolve_extras",
]


def __getattr__(name: str):
    if name == "TemplateGenerator":
        generator_module = __import__(
            "alms_cli.templates.generator",
            fromlist=["TemplateGenerator"],
        )
        return generator_module.TemplateGenerator
    raise AttributeError(name)
