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


def load_config(root: Path | None = None) -> AuditConfig:
    data = tomllib.loads(config_path(root).read_text(encoding="utf-8"))
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
