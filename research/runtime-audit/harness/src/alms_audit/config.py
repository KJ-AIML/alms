"""Load audit configuration from `<root>/configs/audit.default.toml` (stdlib tomllib)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .schemas import default_root


@dataclass(frozen=True)
class AuditConfig:
    hard_cap_usd: float | None
    soft_cap_usd: float | None
    max_live_calls: int
    max_output_tokens: int
    default_timeout_ms: int
    retries: int


def config_path(root: Path | None = None) -> Path:
    return (root or default_root()) / "configs" / "audit.default.toml"


def _parse(data: dict) -> AuditConfig:
    budget = data.get("budget", {})
    execution = data.get("execution", {})
    return AuditConfig(
        hard_cap_usd=budget.get("hard_cap_usd"),
        soft_cap_usd=budget.get("soft_cap_usd"),
        max_live_calls=int(budget.get("max_live_calls", 0)),
        max_output_tokens=int(execution.get("max_output_tokens", 256)),
        default_timeout_ms=int(execution.get("default_timeout_ms", 30000)),
        retries=int(execution.get("retries", 0)),
    )


def load_raw(path: Path) -> dict:
    """Parse a config TOML file. Fail-closed: a missing file raises (no silent fallback)."""
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def load_config(root: Path | None = None) -> AuditConfig:
    return _parse(load_raw(config_path(root)))


def load_config_path(path: Path) -> AuditConfig:
    """Load audit controls from an explicit config file (e.g. a first-live override)."""
    return _parse(load_raw(path))


def approved_fixtures(data: dict) -> list[str] | None:
    """The first-live approved fixture set, if this config declares one (else None).

    Represented in the config's [live_acceptance] table rather than hardcoded into the
    generic fixture corpus, so only a first-live override restricts fixture selection.
    """
    accept = data.get("live_acceptance")
    if not accept or "approved_fixtures" not in accept:
        return None
    return list(accept["approved_fixtures"])
