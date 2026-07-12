"""Interpret raw probe evidence into a normalized transcript + result record.

Normalization is a HARNESS concern (DevSpec Section 31): raw evidence is preserved by the
probe, and only here is it mapped into audit semantics. Raw Evidence != Normalized
Interpretation, and missing usage != zero usage. A normalization failure never rewrites or
deletes raw evidence and never triggers an automatic provider retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .normalizers import openai as _default_normalizer
from .pricing import PricingSnapshot
from .schemas import validation_errors

RESULT_SPEC = "alms.dev/runtime-audit-result/v0"


@dataclass(frozen=True)
class Interpretation:
    status: str
    normalized: dict | None  # None when normalization failed / raw was missing
    result: dict
    notes: list[str]


def _usage_block(usage: dict | None, pricing: PricingSnapshot | None) -> dict:
    if not usage:
        # Absent usage stays absent: every token field null, provenance "absent".
        return {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cached_input_tokens": None,
            "reasoning_tokens": None,
            "cost_reported": None,
            "cost_estimated": None,
            "currency": None,
            "provenance": "absent",
            "finality": "final",
        }
    in_tok = usage.get("input_tokens")
    out_tok = usage.get("output_tokens")
    cost_estimated = None
    currency = None
    if pricing is not None and in_tok is not None and out_tok is not None:
        est = (
            Decimal(int(in_tok)) * pricing.input_price_per_million
            + Decimal(int(out_tok)) * pricing.output_price_per_million
        ) / Decimal(1_000_000)
        cost_estimated = float(est)  # schema is number; estimate != billed cost
        currency = "USD"
    return {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": usage.get("total_tokens"),
        "cached_input_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens"),
        "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
        "cost_reported": None,  # the provider does not report a dollar cost
        "cost_estimated": cost_estimated,
        "currency": currency,
        "provenance": "reported",
        "finality": "final",
    }


def _derive_status(capture_kind: str, normalized: dict) -> tuple[str, list[str]]:
    if capture_kind == "error":
        return "ERROR_RUNTIME", ["provider_error"]
    types = {e["type"] for e in normalized.get("events", [])}
    # A refusal, an unknown native event, or a framework transformation: the run completed but
    # produced provider- or framework-specific behavior rather than the plain expected output.
    # Kept distinct from PASS. provider_extension and framework_extension are NOT conflated.
    if "provider_extension" in types:
        notes = ["provider_refusal"] if _has_refusal(normalized) else ["provider_extension"]
        return "PASS_WITH_EXTENSION", notes
    if "framework_extension" in types:
        return "PASS_WITH_EXTENSION", ["framework_extension"]
    return "PASS", []


def _has_refusal(normalized: dict) -> bool:
    return any(
        e.get("data", {}).get("native_type") == "refusal" for e in normalized.get("events", [])
    )


def _result(
    *,
    run_id: str,
    fixture_id: str,
    lane_id: str,
    status: str,
    raw_manifest_ref: str,
    normalized_ref: str | None,
    usage: dict,
    notes: list[str],
) -> dict:
    return {
        "spec": RESULT_SPEC,
        "run_id": run_id,
        "fixture_id": fixture_id,
        "lane_id": lane_id,
        "status": status,
        "normalized_transcript": normalized_ref,
        "raw_manifest": raw_manifest_ref,
        "usage": usage,
        "notes": notes,
    }


def interpret(
    *,
    capture_kind: str,
    raw_obj: object,
    run_id: str,
    fixture_id: str,
    lane_id: str,
    raw_manifest_ref: str,
    response_ref: str,
    normalized_ref: str,
    pricing: PricingSnapshot | None,
    root,
    normalizer=None,
) -> Interpretation:
    """Normalize one fixture's raw evidence and build its schema-valid result record.

    `normalizer` is the runtime-specific normalizer module (defaults to the OpenAI one for
    backward compatibility); it owns both usage extraction and event normalization for its
    raw shape.
    """
    nz = normalizer or _default_normalizer
    usage = _usage_block(nz.extract_usage(capture_kind, raw_obj), pricing)

    try:
        normalized = nz.normalize(capture_kind, raw_obj, raw_manifest_ref, response_ref)
        errors = validation_errors("normalized-transcript", normalized, root)
        if errors:
            raise ValueError("; ".join(errors))
    except Exception as exc:  # noqa: BLE001 - normalization failure is a recorded outcome
        # Raw evidence stays on disk; interpretation is INCONCLUSIVE, no retry.
        result = _result(
            run_id=run_id,
            fixture_id=fixture_id,
            lane_id=lane_id,
            status="INCONCLUSIVE",
            raw_manifest_ref=raw_manifest_ref,
            normalized_ref=None,
            usage=usage,
            notes=[f"normalization_failed: {exc}"],
        )
        return Interpretation("INCONCLUSIVE", None, result, result["notes"])

    status, notes = _derive_status(capture_kind, normalized)
    result = _result(
        run_id=run_id,
        fixture_id=fixture_id,
        lane_id=lane_id,
        status=status,
        raw_manifest_ref=raw_manifest_ref,
        normalized_ref=normalized_ref,
        usage=usage,
        notes=notes,
    )
    return Interpretation(status, normalized, result, notes)
