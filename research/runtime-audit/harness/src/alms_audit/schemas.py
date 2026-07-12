"""Load and validate against the Phase 0 audit evidence schemas.

The schemas live in `<root>/spec/*.schema.json`. This module only loads and validates;
it never performs network or provider calls.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

# Logical name -> spec filename.
SCHEMA_FILES: dict[str, str] = {
    "fixture": "fixture.schema.json",
    "probe-request": "probe-request.schema.json",
    "probe-response": "probe-response.schema.json",
    "normalized-transcript": "normalized-transcript.schema.json",
    "result": "result.schema.json",
    "finding": "finding.schema.json",
    "run-manifest": "run-manifest.schema.json",
}


def default_root() -> Path:
    """The `research/runtime-audit/` directory this package ships inside.

    ponytail: assumes the editable source layout (harness/src/alms_audit/...), which
    is how `uv sync` installs a local project. Override with `--root` for any other case.
    """
    return Path(__file__).resolve().parents[3]


def spec_dir(root: Path | None = None) -> Path:
    return (root or default_root()) / "spec"


def load_schema(name: str, root: Path | None = None) -> dict:
    if name not in SCHEMA_FILES:
        raise KeyError(f"unknown schema {name!r}; known: {sorted(SCHEMA_FILES)}")
    path = spec_dir(root) / SCHEMA_FILES[name]
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator_cached(name: str, root_str: str) -> Draft202012Validator:
    schema = load_schema(name, Path(root_str))
    Draft202012Validator.check_schema(schema)  # the schema itself must be well-formed
    return Draft202012Validator(schema)


def validator_for(name: str, root: Path | None = None) -> Draft202012Validator:
    return _validator_cached(name, str(root or default_root()))


def validation_errors(name: str, instance: object, root: Path | None = None) -> list[str]:
    """Return human-readable errors for `instance` against schema `name` (empty == valid)."""
    validator = validator_for(name, root)
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    ]


def is_valid(name: str, instance: object, root: Path | None = None) -> bool:
    return not validation_errors(name, instance, root)
