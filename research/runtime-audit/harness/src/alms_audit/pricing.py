"""Pricing snapshot + upper-bound cost gate (DevSpec Section 80).

The dollar budget must not be ceremonial. A live plan carries an explicit, non-secret
pricing snapshot sufficient to compute an UPPER BOUND on cost before any provider call.
Pricing is never fetched dynamically and never silently updated: it is committed config,
recorded by digest in the run manifest. The estimate is a safety upper bound, NOT an
accounting claim; actual usage and actual cost are separate evidence after execution.

All arithmetic uses Decimal, never binary float, so budget comparisons are exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_PER_MILLION = Decimal(1_000_000)


class CostError(RuntimeError):
    """Raised to refuse a live/offline plan whose cost cannot be safely upper-bounded."""


@dataclass(frozen=True)
class PricingSnapshot:
    model_id: str
    price_checked_at: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    estimated_input_tokens_per_call: int
    maximum_output_tokens_per_call: int
    maximum_calls: int
    pricing_source_note: str

    def as_evidence(self) -> dict:
        """Non-secret snapshot recorded in the run manifest / plan (JSON-safe)."""
        return {
            "model_id": self.model_id,
            "price_checked_at": self.price_checked_at,
            "input_price_per_million": str(self.input_price_per_million),
            "output_price_per_million": str(self.output_price_per_million),
            "estimated_input_tokens_per_call": self.estimated_input_tokens_per_call,
            "maximum_output_tokens_per_call": self.maximum_output_tokens_per_call,
            "maximum_calls": self.maximum_calls,
            "pricing_source_note": self.pricing_source_note,
        }


def _dec(value: object, field: str, model_id: str) -> Decimal:
    try:
        # str() so a TOML float never enters Decimal as binary noise; TOML strings preferred.
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise CostError(f"pricing[{model_id}].{field}: not a valid decimal: {value!r}") from exc


def snapshot_from_dict(entry: dict) -> PricingSnapshot:
    """Parse one committed pricing entry, failing closed on absent/malformed prices."""
    model_id = entry.get("model_id")
    if not model_id:
        raise CostError("pricing entry missing model_id")
    required = (
        "price_checked_at",
        "input_price_per_million",
        "output_price_per_million",
        "estimated_input_tokens_per_call",
        "maximum_output_tokens_per_call",
        "maximum_calls",
        "pricing_source_note",
    )
    missing = [k for k in required if k not in entry]
    if missing:
        raise CostError(f"pricing[{model_id}] missing fields: {', '.join(missing)}")

    in_price = _dec(entry["input_price_per_million"], "input_price_per_million", model_id)
    out_price = _dec(entry["output_price_per_million"], "output_price_per_million", model_id)
    # Zero or negative prices are a broken snapshot, not a free/cheap model. Fail closed.
    if in_price <= 0 or out_price <= 0:
        raise CostError(
            f"pricing[{model_id}]: prices must be positive (input={in_price}, output={out_price})"
        )
    est_in = int(entry["estimated_input_tokens_per_call"])
    max_out = int(entry["maximum_output_tokens_per_call"])
    max_calls = int(entry["maximum_calls"])
    if est_in < 0 or max_out < 0 or max_calls < 0:
        raise CostError(f"pricing[{model_id}]: token/call counts must be non-negative")

    return PricingSnapshot(
        model_id=model_id,
        price_checked_at=str(entry["price_checked_at"]),
        input_price_per_million=in_price,
        output_price_per_million=out_price,
        estimated_input_tokens_per_call=est_in,
        maximum_output_tokens_per_call=max_out,
        maximum_calls=max_calls,
        pricing_source_note=str(entry["pricing_source_note"]),
    )


def load_snapshots(config_data: dict) -> dict[str, PricingSnapshot]:
    """Read all `[[pricing]]` snapshots from a parsed config into a model_id -> snapshot map."""
    snaps: dict[str, PricingSnapshot] = {}
    for entry in config_data.get("pricing", []):
        snap = snapshot_from_dict(entry)
        snaps[snap.model_id] = snap
    return snaps


def upper_bound_cost(snapshot: PricingSnapshot, calls: int) -> Decimal:
    """Worst-case Decimal cost for `calls` calls: max output tokens, estimated input tokens."""
    per_call = (
        Decimal(snapshot.estimated_input_tokens_per_call) * snapshot.input_price_per_million
        + Decimal(snapshot.maximum_output_tokens_per_call) * snapshot.output_price_per_million
    ) / _PER_MILLION
    return per_call * Decimal(calls)


def gate_cost(
    snapshot: PricingSnapshot | None,
    *,
    model_id: str,
    expected_calls: int,
    hard_cap_usd: float | None,
) -> Decimal:
    """Fail closed unless an upper-bound cost can be computed and is within the hard cap.

    Refuses when: pricing is absent, the snapshot model does not match the selected model,
    the estimate cannot be calculated, or the estimate exceeds the hard cap.
    Returns the Decimal upper-bound estimate when the gate passes.
    """
    if snapshot is None:
        raise CostError(f"no pricing snapshot for model {model_id!r}; cannot bound cost")
    if snapshot.model_id != model_id:
        raise CostError(
            f"pricing snapshot model {snapshot.model_id!r} does not match "
            f"selected model {model_id!r}"
        )
    if hard_cap_usd is None:
        raise CostError("cannot gate cost: hard budget cap is absent")
    estimate = upper_bound_cost(snapshot, expected_calls)
    if estimate > Decimal(str(hard_cap_usd)):
        raise CostError(
            f"upper-bound cost estimate {estimate} USD exceeds hard cap {hard_cap_usd} USD"
        )
    return estimate
