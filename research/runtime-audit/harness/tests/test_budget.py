"""Budget guard tests (DevSpec Section 80): fail closed without a valid budget."""

from __future__ import annotations

import pytest

from alms_audit.budget import BudgetError, check_call_cap, check_live_budget
from alms_audit.config import AuditConfig


def _cfg(hard_cap, max_calls=80) -> AuditConfig:
    return AuditConfig(
        hard_cap_usd=hard_cap,
        soft_cap_usd=2.0,
        max_live_calls=max_calls,
        max_output_tokens=256,
        default_timeout_ms=30000,
        retries=0,
    )


@pytest.mark.parametrize("hard_cap", [None, 0, 0.0, -5])
def test_live_budget_absent_or_nonpositive_is_refused(hard_cap) -> None:
    with pytest.raises(BudgetError):
        check_live_budget(_cfg(hard_cap))


def test_live_budget_present_is_allowed() -> None:
    check_live_budget(_cfg(15.0))  # no raise


def test_call_cap_exceeded_is_refused() -> None:
    with pytest.raises(BudgetError):
        check_call_cap(81, _cfg(15.0, max_calls=80))


def test_call_cap_within_limit_is_allowed() -> None:
    check_call_cap(80, _cfg(15.0, max_calls=80))
