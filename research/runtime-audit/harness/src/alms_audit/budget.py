"""Budget guard (DevSpec Section 80). Fails closed: no valid budget means no live run."""

from __future__ import annotations

from .config import AuditConfig


class BudgetError(RuntimeError):
    """Raised to refuse a live run whose budget/call ceiling is missing or exceeded."""


def check_live_budget(config: AuditConfig) -> None:
    """A live run requires a present, positive hard cap. Absence/zero fails closed."""
    if config.hard_cap_usd is None or config.hard_cap_usd <= 0:
        raise BudgetError(
            "live run refused: hard budget cap is absent or non-positive "
            f"(hard_cap_usd={config.hard_cap_usd!r})"
        )


def check_call_cap(expected_calls: int, config: AuditConfig) -> None:
    if expected_calls > config.max_live_calls:
        raise BudgetError(
            f"live run refused: expected {expected_calls} calls exceeds "
            f"max_live_calls={config.max_live_calls}"
        )
