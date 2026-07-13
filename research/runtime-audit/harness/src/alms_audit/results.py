"""Interpret raw probe evidence into a normalized transcript + result record.

Normalization is a HARNESS concern (DevSpec Section 31): raw evidence is preserved by the
probe, and only here is it mapped into audit semantics. Raw Evidence != Normalized
Interpretation, and missing usage != zero usage. A normalization failure never rewrites or
deletes raw evidence and never triggers an automatic provider retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from . import provenance
from .normalizers import openai as _default_normalizer
from .pricing import PricingSnapshot
from .schemas import validation_errors

RESULT_SPEC = "alms.dev/runtime-audit-result/v0"

# Native terminal string -> coarse audit terminal category. Unknown natives are NOT dropped:
# they are recorded verbatim in `native` with category "unknown".
_TERMINAL_CATEGORY = {
    "completed": "completed",
    "end_turn": "completed",
    "stop": "completed",
    "stop_sequence": "completed",
    "incomplete": "incomplete",
    "failed": "error",
    "error": "error",
    "cancelled": "cancelled",
    "requires_action": "requires_action",
    "tool_use": "requires_action",
    "budget_exceeded": "budget_exceeded",
    "refusal": "refusal",
    "content_filter": "refusal",
    "max_tokens": "max_tokens",
    "length": "max_tokens",
}


@dataclass(frozen=True)
class Interpretation:
    status: str
    normalized: dict | None  # None when normalization failed / raw was missing
    result: dict
    notes: list[str]


def _usage_block(summary: dict | None, pricing: PricingSnapshot | None) -> dict:
    """Build the result usage record from a normalizer's NEUTRAL usage summary.

    The summary is provider-shape-agnostic (see each normalizer's `_summarize`): it carries
    input/output/total, a cache_read + cache_creation split, reasoning tokens, and a `source`
    provenance tag. This function no longer reads any provider-specific nested key path, so a
    non-OpenAI provider's cache/reasoning tokens are no longer dropped. `source` records whether
    the figure is provider-native or framework-normalized; `provenance` records reported-vs-
    absent. Missing usage stays null (never 0).
    """
    if not summary:
        # Absent usage stays absent: every token field null, provenance "absent".
        return {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cached_input_tokens": None,
            "cache_read_input_tokens": None,
            "cache_creation_input_tokens": None,
            "reasoning_tokens": None,
            "cost_reported": None,
            "cost_estimated": None,
            "currency": None,
            "provenance": "absent",
            "source": provenance.UNAVAILABLE,
            "finality": "final",
        }
    in_tok = summary.get("input_tokens")
    out_tok = summary.get("output_tokens")
    cost_estimated = None
    currency = None
    if pricing is not None and in_tok is not None and out_tok is not None:
        est = (
            Decimal(int(in_tok)) * pricing.input_price_per_million
            + Decimal(int(out_tok)) * pricing.output_price_per_million
        ) / Decimal(1_000_000)
        cost_estimated = float(est)  # schema is number; estimate != billed cost
        currency = "USD"
    cache_read = summary.get("cache_read_input_tokens")
    return {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": summary.get("total_tokens"),
        "cached_input_tokens": cache_read,  # back-compat alias == cache_read_input_tokens
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": summary.get("cache_creation_input_tokens"),
        "reasoning_tokens": summary.get("reasoning_tokens"),
        "cost_reported": None,  # the provider does not report a dollar cost
        "cost_estimated": cost_estimated,  # harness-computed: a local_estimate
        "currency": currency,
        "provenance": "reported",
        "source": summary.get("source", provenance.PROVIDER_NATIVE),
        "finality": "final",
    }


def _terminal_state(normalized: dict | None, source: str) -> dict | None:
    """The runtime-native terminal signal, made queryable at the result level (P0.6C).

    result.status is the AUDIT verdict; this is a different axis — the provider/framework
    terminal state (completed / incomplete / requires_action / refusal / budget_exceeded /
    error / max_tokens / ...). It is read back out of the normalized transcript's terminal and
    error events, so it never contradicts the preserved evidence. An unrecognized native string
    is kept verbatim with category "unknown" rather than dropped.
    """
    if not normalized:
        return None
    native = None
    for e in normalized.get("events", []):
        d = e.get("data", {}) or {}
        etype = e.get("type")
        if etype == "response_completed":
            native = d.get("status") or d.get("stop_reason") or d.get("finish_reason") or native
        elif etype == "error":
            native = native or d.get("native_type") or "error"
    src = (
        source
        if source in (provenance.PROVIDER_NATIVE, provenance.FRAMEWORK_NATIVE)
        else provenance.UNAVAILABLE
    )
    if native is None:
        return {"native": None, "category": "unknown", "source": src}
    return {"native": native, "category": _TERMINAL_CATEGORY.get(native, "unknown"), "source": src}


def _model_identity(
    nz,
    capture_kind: str,
    raw_obj: object,
    requested_model: str | None,
    execution_mode: str | None,
    response_ref: str | None,
) -> dict:
    """Neutral cross-lane model identity summary (P0.6D, finding N-05).

    This shared builder holds NO provider-specific extraction path: it delegates to the lane
    normalizer's ``extract_model_identity`` (each reads its own native shape) and assembles the
    neutral contract. The requested model (request-side config) is never overwritten by the
    observation, and the observation is never fabricated from the requested model:

      * observed absent  -> observed_returned_model = None, source = ``unavailable``, no raw_ref.
      * observed present, offline_mock -> source = ``fixture_expected`` (synthetic, NOT provider/
        framework-native), raw_ref points at the raw artifact.
      * observed present, live -> source = the lane's live source (provider_native for a native
        lane, framework_native for a framework lane).

    ``model_identity_match`` is an EXACT-STRING comparison (no canonicalization) and is purely
    observational: a mismatch is recorded, never turned into an error here.
    """
    observed = None
    extractor = getattr(nz, "extract_model_identity", None)
    if extractor is not None:
        try:
            observed = extractor(capture_kind, raw_obj)
        except Exception:  # noqa: BLE001 - a broken extractor yields unavailable, never a crash
            observed = None

    if not observed:
        return {
            "requested_model": requested_model,
            "observed_returned_model": None,
            "observed_returned_model_source": provenance.UNAVAILABLE,
            "observed_returned_model_raw_ref": None,
            "execution_mode": execution_mode,
            "model_identity_match": "unknown",
        }

    if execution_mode == "live":
        source = getattr(nz, "MODEL_IDENTITY_LIVE_SOURCE", provenance.PROVIDER_NATIVE)
    else:
        # Offline synthetic evidence (or unknown mode) is fixture_expected, never provider/
        # framework-native: an offline provider-shaped object is not a real provider observation.
        source = provenance.FIXTURE_EXPECTED
    if requested_model is None:
        match = "unknown"
    else:
        match = "true" if observed == requested_model else "false"
    return {
        "requested_model": requested_model,
        "observed_returned_model": observed,
        "observed_returned_model_source": source,
        "observed_returned_model_raw_ref": response_ref,
        "execution_mode": execution_mode,
        "model_identity_match": match,
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
    terminal_state: dict | None = None,
    model_identity: dict | None = None,
) -> dict:
    result = {
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
    if terminal_state is not None:
        result["observed_terminal_state"] = terminal_state
    if model_identity is not None:
        result["observed_model_identity"] = model_identity
    return result


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
    requested_model: str | None = None,
    execution_mode: str | None = None,
) -> Interpretation:
    """Normalize one fixture's raw evidence and build its schema-valid result record.

    `normalizer` is the runtime-specific normalizer module (defaults to the OpenAI one for
    backward compatibility); it owns usage extraction, model-identity extraction, and event
    normalization for its raw shape. `requested_model` and `execution_mode` come from the probe
    manifest and drive the neutral model-identity summary (P0.6D); both are optional so existing
    callers stay backward compatible.
    """
    nz = normalizer or _default_normalizer
    usage = _usage_block(nz.extract_usage(capture_kind, raw_obj), pricing)
    usage_source = getattr(nz, "USAGE_SOURCE", provenance.PROVIDER_NATIVE)
    model_identity = _model_identity(
        nz, capture_kind, raw_obj, requested_model, execution_mode, response_ref
    )

    try:
        normalized = nz.normalize(capture_kind, raw_obj, raw_manifest_ref, response_ref)
        errors = validation_errors("normalized-transcript", normalized, root)
        if errors:
            raise ValueError("; ".join(errors))
    except Exception as exc:  # noqa: BLE001 - normalization failure is a recorded outcome
        # Raw evidence stays on disk; interpretation is INCONCLUSIVE, no retry. Model identity is
        # still recorded: the requested model and any observed returned model are known from the
        # manifest + raw artifact even when transcript normalization failed.
        result = _result(
            run_id=run_id,
            fixture_id=fixture_id,
            lane_id=lane_id,
            status="INCONCLUSIVE",
            raw_manifest_ref=raw_manifest_ref,
            normalized_ref=None,
            usage=usage,
            notes=[f"normalization_failed: {exc}"],
            model_identity=model_identity,
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
        terminal_state=_terminal_state(normalized, usage_source),
        model_identity=model_identity,
    )
    return Interpretation(status, normalized, result, notes)
