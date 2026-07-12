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


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


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

    return {
        "probe_id": manifest.get("probe_id"),
        "capture_kind": manifest.get("capture_kind"),
        "execution_mode": manifest.get("execution_mode"),
        "package_versions": manifest.get("package_versions", {}),
        "retry_count_observed": manifest.get("retry_count_observed"),
        "raw_artifact_categories": raw_artifacts,
        "event_representation": event_types,
        "tool_call_representation": [
            {"name": t["data"].get("name"), "has_call_id": bool(t["data"].get("call_id"))}
            for t in tool_calls
        ],
        "structured_output_strategy": (structured or {}).get("data", {}).get("strategy"),
        "usage_representation": {
            "present": bool(usage_events),
            "provenance": result.get("usage", {}).get("provenance"),
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
        "openai_run": str(openai_run),
        "langchain_run": str(langchain_run),
        "fixtures": [compare_fixture(openai_run, langchain_run, f) for f in fixture_ids],
    }
