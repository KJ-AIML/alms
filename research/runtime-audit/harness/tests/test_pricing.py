"""Pricing snapshot + Decimal upper-bound cost gate tests (DevSpec Section 80)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from alms_audit.config import load_raw
from alms_audit.pricing import (
    CostError,
    gate_cost,
    load_snapshots,
    snapshot_from_dict,
    upper_bound_cost,
)
from alms_audit.schemas import default_root

_BASE = {
    "model_id": "gpt-5.4-nano-2026-03-17",
    "price_checked_at": "2026-07-13",
    "input_price_per_million": "0.20",
    "output_price_per_million": "1.25",
    "estimated_input_tokens_per_call": 500,
    "maximum_output_tokens_per_call": 128,
    "maximum_calls": 8,
    "pricing_source_note": "test",
}


def test_first_live_config_has_pricing_snapshot_for_model():
    data = load_raw(default_root() / "configs" / "first-live.override.toml")
    snaps = load_snapshots(data)
    assert "gpt-5.4-nano-2026-03-17" in snaps


def test_upper_bound_cost_is_exact_decimal():
    snap = snapshot_from_dict(_BASE)
    # per call: 500*0.20/1e6 + 128*1.25/1e6 = 0.0001 + 0.00016 = 0.00026; x8 = 0.00208
    assert upper_bound_cost(snap, 8) == Decimal("0.00208")
    assert isinstance(upper_bound_cost(snap, 8), Decimal)


def test_gate_passes_within_hard_cap_and_returns_estimate():
    snap = snapshot_from_dict(_BASE)
    est = gate_cost(snap, model_id="gpt-5.4-nano-2026-03-17", expected_calls=6, hard_cap_usd=1.00)
    assert est == Decimal("0.00156")


def test_gate_rejects_missing_snapshot():
    with pytest.raises(CostError):
        gate_cost(None, model_id="gpt-5.4-nano-2026-03-17", expected_calls=6, hard_cap_usd=1.00)


def test_gate_rejects_model_mismatch():
    snap = snapshot_from_dict(_BASE)
    with pytest.raises(CostError, match="does not match"):
        gate_cost(snap, model_id="some-other-model", expected_calls=6, hard_cap_usd=1.00)


def test_gate_rejects_estimate_over_hard_cap():
    snap = snapshot_from_dict(_BASE)
    # A boundary just below the estimate must be refused.
    with pytest.raises(CostError, match="exceeds hard cap"):
        gate_cost(snap, model_id="gpt-5.4-nano-2026-03-17", expected_calls=8, hard_cap_usd=0.002)


def test_gate_boundary_estimate_equal_to_cap_passes():
    snap = snapshot_from_dict(_BASE)
    # estimate for 8 calls == 0.00208; a cap exactly equal must pass (not >).
    est = gate_cost(
        snap, model_id="gpt-5.4-nano-2026-03-17", expected_calls=8, hard_cap_usd=0.00208
    )
    assert est == Decimal("0.00208")


def test_gate_rejects_absent_hard_cap():
    snap = snapshot_from_dict(_BASE)
    with pytest.raises(CostError):
        gate_cost(snap, model_id="gpt-5.4-nano-2026-03-17", expected_calls=6, hard_cap_usd=None)


@pytest.mark.parametrize("field", ["input_price_per_million", "output_price_per_million"])
def test_zero_and_negative_prices_rejected(field):
    for bad in ("0", "0.00", "-0.20"):
        entry = dict(_BASE, **{field: bad})
        with pytest.raises(CostError, match="positive"):
            snapshot_from_dict(entry)


def test_missing_pricing_field_rejected():
    entry = dict(_BASE)
    del entry["input_price_per_million"]
    with pytest.raises(CostError, match="missing"):
        snapshot_from_dict(entry)
