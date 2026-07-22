"""Native Phase 0 gate preservation checks for compatibility lab."""

from __future__ import annotations

from typing import Any

# Frozen snapshot of Phase 0 states that C0 must not alter.
PHASE0_PRESERVED: dict[str, Any] = {
    "G2": "blocked_credential",
    "G3": "blocked_credential",
    "G7": "not_started",
    "L-01": {"severity": "F2", "status": "proposed"},
    "phase0_complete": False,
    "phase1_entry_approved": False,
    "draft_model_runtime_forbidden": True,
    "mandatory_offline_campaign": "ALL_ELIGIBLE_OFFLINE_WORK_COMPLETE",
}

NATIVE_LANES = frozenset(
    {
        "openai-native",
        "anthropic-native",
        "gemini-native",
        "langchain",
        "litellm-sdk",
        "pydantic-ai-agent",
    }
)

COMPAT_LANES = frozenset({"openai-compatible-custom", "anthropic-compatible-custom"})


def assert_gates_preserved(snapshot: dict[str, Any]) -> None:
    for key, expected in PHASE0_PRESERVED.items():
        actual = snapshot.get(key)
        if actual != expected:
            raise AssertionError(
                f"native gate contamination: {key}={actual!r} expected {expected!r}"
            )


def custom_lanes_absent_from_native(native_lane_ids: set[str]) -> bool:
    return COMPAT_LANES.isdisjoint(native_lane_ids)
