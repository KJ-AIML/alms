"""Interpret raw probe evidence into a normalized transcript + result record.

Normalization is a HARNESS concern (DevSpec Section 31): raw evidence is preserved by the
probe, and only here is it mapped into audit semantics. Raw Evidence != Normalized
Interpretation, and missing usage != zero usage. A normalization failure never rewrites or
deletes raw evidence and never triggers an automatic provider retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .normalizers import openai as nz
from .pricing import PricingSnapshot
from .schemas import validation_errors

RESULT_SPEC = "alms.dev/runtime-audit-result/v0"


@dataclass(frozen=True)
class Interpretation:
    status: str
    normalized: dict | None  # None when normalization failed / raw was missing
    result: dict
    notes: list[str]


def _extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """Provider-reported usage, or None when the provider did not report any.

    None (absent) is preserved distinctly; it is never coerced to zero.
    """
    if capture_kind == "response" and isinstance(raw_obj, dict):
        return raw_obj.get("usage")
    if capture_kind == "stream" and isinstance(raw_obj, list):
        for ev in raw_obj:
            data = ev.get("data") if isinstance(ev, dict) else None
            if isinstance(ev, dict) and ev.get("type") == "response.completed":
                resp = (data or {}).get("response", {}) if isinstance(data, dict) else {}
                return resp.get("usage")
    return None


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


def _normalize(capture_kind: str, raw_obj: object, raw_manifest_ref: str, response_ref: str):
    if capture_kind == "stream":
        return nz.normalize_stream(raw_obj, raw_manifest_ref, response_ref)
    if capture_kind == "error":
        return nz.normalize_error(raw_obj, raw_manifest_ref, response_ref)
    return nz.normalize_response(raw_obj, raw_manifest_ref, response_ref)


def _derive_status(capture_kind: str, normalized: dict) -> tuple[str, list[str]]:
    if capture_kind == "error":
        return "ERROR_RUNTIME", ["provider_error"]
    types = {e["type"] for e in normalized.get("events", [])}
    if "provider_extension" in types:
        # A refusal or an unknown native event: the run completed but produced provider-
        # specific behavior rather than the plain expected output. Kept distinct from PASS.
        notes = ["provider_refusal"] if _has_refusal(normalized) else ["provider_extension"]
        return "PASS_WITH_EXTENSION", notes
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
) -> Interpretation:
    """Normalize one fixture's raw evidence and build its schema-valid result record."""
    usage = _usage_block(_extract_usage(capture_kind, raw_obj), pricing)

    try:
        normalized = _normalize(capture_kind, raw_obj, raw_manifest_ref, response_ref)
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
