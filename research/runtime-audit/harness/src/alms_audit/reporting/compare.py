"""Preliminary OFFLINE comparison of the openai-native and langchain lanes.

This consumes existing offline-mock run evidence and reports how the two lanes' captured
SHAPES differ. It is deliberately conservative about what that means:

    This is implementation-shape evidence only.
    It is not live provider semantic evidence.

Both lanes ran against injected fakes, so a difference here reflects how each probe and its
runtime represent a mock interaction offline, not a verified provider-behavior difference.
Differences caused by a verified framework API behavior (e.g. LangChain requiring a schema
title, or using tool-calling for structured output) are the interesting ones; differences
that are merely mock-shape artifacts are not findings. The report never derives an F1 by
itself.
"""

from __future__ import annotations

import json
from pathlib import Path

DISCLAIMER = (
    "This is implementation-shape evidence only. It is not live provider semantic evidence. "
    "Both lanes used injected offline fakes; a shape difference is not by itself a finding."
)

MODEL_IDENTITY_NOTE = (
    "Observed returned model values in this report are synthetic offline evidence unless "
    "explicitly marked live (execution_mode). A requested/observed mismatch offline reflects the "
    "mock fixture, NOT verified provider alias/snapshot/gateway routing; that remains "
    "unverified_until_live. No provider routing behavior is inferred from these offline values."
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _structured_mechanism(probe_id: str | None, strategy: str | None, has_structured: bool):
    """Classify the structured-output mechanism a lane actually used.

    After the P0.6A correction, both NATIVE lanes expose provider-native JSON-schema output
    (OpenAI Responses API json_schema; Anthropic Messages API output_config.format), while the
    LangChain offline lane selected a framework-mediated function-calling strategy. This is
    implementation-shape evidence only.
    """
    if not has_structured:
        return None
    if strategy == "function_calling":
        return "framework_function_calling"
    if strategy == "response_format.json_schema":
        # LiteLLM translates an OpenAI-style response_format; the JSON is framework-mediated and
        # provider validation is unverified_until_live. NOT native provider JSON-schema proof.
        return "framework_response_format (litellm sdk)"
    if strategy == "native_output":
        # PydanticAI NativeOutput: the framework selects native mode, generates the JSON Schema,
        # and parses/validates offline against a SYNTHETIC model profile. It is framework-mediated;
        # a real provider following native JSON schema is unverified_until_live. NOT provider-native
        # JSON-schema proof, so it does NOT join the native_json_schema family.
        return "framework_native_output (pydanticai)"
    if strategy == "output_config.format":
        return "native_json_schema (anthropic messages output_config.format)"
    if strategy == "response_format.text.json_schema":
        return "native_json_schema (gemini interactions response_format)"
    if probe_id == "openai-native":
        # The OpenAI probe requests native json_schema on the Responses API (text.format).
        return "native_json_schema (openai responses api)"
    return strategy or "unknown"


def _fixture_view(run_dir: Path, fixture_id: str) -> dict:
    fx = run_dir / "fixtures" / fixture_id
    manifest = _read(fx / "probe-response.json")
    transcript = _read(fx / "normalized-transcript.json")
    result = _read(fx / "result.json")
    response = _read(Path(manifest["response_path"])) if manifest.get("response_path") else {}

    events = transcript.get("events", [])
    event_types = [e.get("type") for e in events]
    tool_calls = [e for e in events if e.get("type") == "tool_call_completed"]
    structured = next((e for e in events if e.get("type") == "structured_output_completed"), None)
    usage_events = [e for e in events if e.get("type") == "usage_updated"]

    raw_dir = fx / "raw"
    raw_artifacts = sorted(p.name for p in raw_dir.glob("*")) if raw_dir.is_dir() else []

    strategy = (structured or {}).get("data", {}).get("strategy")
    mechanism = _structured_mechanism(manifest.get("probe_id"), strategy, structured is not None)

    mi = result.get("observed_model_identity") or {}
    observed_model = mi.get("observed_returned_model")

    # Per-fixture execution-path classification (litellm-sdk records this in its raw envelope; other
    # lanes do not, so it stays None). Evidence accuracy: not all fixtures share one path.
    exec_path = response.get("execution_path") if isinstance(response, dict) else None

    return {
        "probe_id": manifest.get("probe_id"),
        "capture_kind": manifest.get("capture_kind"),
        "execution_mode": manifest.get("execution_mode"),
        "execution_path": exec_path,
        "package_versions": manifest.get("package_versions", {}),
        "retry_count_observed": manifest.get("retry_count_observed"),
        "raw_artifact_categories": raw_artifacts,
        "event_representation": event_types,
        "tool_call_representation": [
            {"name": t["data"].get("name"), "has_call_id": bool(t["data"].get("call_id"))}
            for t in tool_calls
        ],
        "structured_output_strategy": strategy,
        "structured_output_mechanism": mechanism,
        "structured_output_is_native_json_schema": bool(mechanism)
        and mechanism.startswith("native_json_schema"),
        "usage_representation": {
            "present": bool(usage_events),
            "provenance": result.get("usage", {}).get("provenance"),
        },
        "model_identity": {
            "requested_model": mi.get("requested_model"),
            "observed_returned_model": observed_model,
            "observed_returned_model_source": mi.get("observed_returned_model_source"),
            "raw_reference_present": bool(mi.get("observed_returned_model_raw_ref")),
            "requested_observed_exact_match": mi.get("model_identity_match"),
            "availability": "available" if observed_model else "unavailable",
            "execution_mode": mi.get("execution_mode"),
        },
        "extension_events": {
            "provider_extension": event_types.count("provider_extension"),
            "framework_extension": event_types.count("framework_extension"),
        },
        "error_representation": (
            response.get("framework_exception_type") or response.get("exception_type")
            if manifest.get("capture_kind") == "error"
            else None
        ),
        "status": result.get("status"),
    }


def compare_fixture(openai_run: Path, langchain_run: Path, fixture_id: str) -> dict:
    a = _fixture_view(openai_run, fixture_id)
    b = _fixture_view(langchain_run, fixture_id)
    return {
        "fixture_id": fixture_id,
        "openai_native": a,
        "langchain": b,
        "same_status": a["status"] == b["status"],
        "same_event_sequence": a["event_representation"] == b["event_representation"],
        "structured_strategy_differs": a["structured_output_strategy"]
        != b["structured_output_strategy"],
        "framework_added_extension": b["extension_events"]["framework_extension"]
        > a["extension_events"]["framework_extension"],
    }


def compare_lanes(openai_run: Path, langchain_run: Path, fixture_ids: list[str]) -> dict:
    """Return a structured, disclaimer-tagged comparison across the given fixtures."""
    return {
        "disclaimer": DISCLAIMER,
        "model_identity_note": MODEL_IDENTITY_NOTE,
        "openai_run": str(openai_run),
        "langchain_run": str(langchain_run),
        "fixtures": [compare_fixture(openai_run, langchain_run, f) for f in fixture_ids],
    }


def compare_runs(runs: dict[str, Path], fixture_ids: list[str]) -> dict:
    """Compare an arbitrary set of lanes ({lane_label: run_dir}) across fixtures.

    Used for the P0.6A three-lane diversity comparison (openai-native / langchain /
    anthropic-native). Still implementation-shape only — see DISCLAIMER. Each fixture view is
    keyed by lane so callers can inspect system-role, content-block, structured-output, tool,
    stream, usage, and extension differences without the report deciding what they mean.
    """
    return {
        "disclaimer": DISCLAIMER,
        "model_identity_note": MODEL_IDENTITY_NOTE,
        "lanes": {label: str(run) for label, run in runs.items()},
        "fixtures": [
            {
                "fixture_id": f,
                "by_lane": {label: _fixture_view(run, f) for label, run in runs.items()},
                "model_identity_by_lane": {
                    label: _fixture_view(run, f)["model_identity"] for label, run in runs.items()
                },
                "structured_strategies": {
                    label: _fixture_view(run, f)["structured_output_strategy"]
                    for label, run in runs.items()
                },
                "structured_mechanisms": {
                    label: _fixture_view(run, f)["structured_output_mechanism"]
                    for label, run in runs.items()
                },
                "native_json_schema_lanes": sorted(
                    label
                    for label, run in runs.items()
                    if _fixture_view(run, f)["structured_output_is_native_json_schema"]
                ),
                # Evidence accuracy: the execution path is NOT identical across a lane's fixtures
                # (e.g. litellm-sdk TOOL-001 is request-transform + response-object-injection, not
                # the full completion(tools=...) path). None for lanes that do not classify paths.
                "execution_path_by_lane": {
                    label: _fixture_view(run, f)["execution_path"] for label, run in runs.items()
                },
            }
            for f in fixture_ids
        ],
    }
