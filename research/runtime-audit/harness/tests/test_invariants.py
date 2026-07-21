"""Unit tests for deterministic invariant evaluators (P0.7D-invariants)."""

from __future__ import annotations

from alms_audit.invariants import evaluate_invariants

VALID_TRANSCRIPT = {
    "spec": "alms.dev/normalized-transcript/v0",
    "raw_manifest": "runs/r1/raw-manifest.json",
    "events": [
        {
            "sequence": 0,
            "type": "response_started",
            "timestamp_relative_ms": 0,
            "data": {},
            "raw_ref": "runs/r1/response.json#0",
        }
    ],
}

VALID_RESULT = {
    "spec": "alms.dev/runtime-audit-result/v0",
    "run_id": "r1",
    "fixture_id": "GEN-001",
    "lane_id": "openai-native",
    "status": "PASS",
    "raw_manifest": "runs/r1/raw-manifest.json",
}


def _usage(provenance: str, **tokens: int | None) -> dict:
    base = {
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
        "provenance": provenance,
        "source": "unavailable",
        "finality": "final",
    }
    base.update(tokens)
    return base


def _transcript(*events: dict) -> dict:
    return {
        "spec": "alms.dev/normalized-transcript/v0",
        "raw_manifest": "runs/r1/raw-manifest.json",
        "events": list(events),
    }


def _event(seq: int, etype: str, data: dict | None = None) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data or {},
        "raw_ref": f"runs/r1/raw#{seq}",
    }


def _gen001_fixture() -> dict:
    return {
        "spec": "alms.dev/runtime-audit-fixture/v0",
        "id": "GEN-001",
        "feature": "generation",
        "summary": "Basic text generation",
        "messages": [{"role": "user", "parts": [{"kind": "text", "text": "Hi"}]}],
        "requirements": {"live_required": True, "capabilities": ["generation"]},
        "execution": {},
        "expected_invariants": {
            "non_empty_assistant_content": True,
            "terminal_state_present": True,
        },
        "allowed_outcomes": ["PASS"],
        "evidence_requirements": {"raw": ["raw_response"], "normalized": ["response_completed"]},
    }


def test_usage_not_fabricated_passes_on_absent_nulls() -> None:
    result = {**VALID_RESULT, "usage": _usage("absent")}
    out = evaluate_invariants(
        {"expected_invariants": {"usage_not_fabricated": True}},
        result,
        VALID_TRANSCRIPT,
    )
    assert out[0]["passed"] is True
    assert out[0]["mode"] == "deterministic"


def test_usage_not_fabricated_fails_if_tokens_zero_with_absent_provenance() -> None:
    result = {
        **VALID_RESULT,
        "usage": _usage("absent", input_tokens=0, output_tokens=0, total_tokens=0),
    }
    out = evaluate_invariants(
        {"expected_invariants": {"usage_not_fabricated": True}},
        result,
        VALID_TRANSCRIPT,
    )
    assert out[0]["passed"] is False
    assert "absent" in out[0]["detail"]


def test_terminal_state_present_positive() -> None:
    result = {
        **VALID_RESULT,
        "observed_terminal_state": {
            "native": "completed",
            "category": "completed",
            "source": "provider_native",
        },
    }
    out = evaluate_invariants(
        {"expected_invariants": {"terminal_state_present": True}},
        result,
        VALID_TRANSCRIPT,
    )
    assert out[0]["passed"] is True


def test_terminal_state_present_negative() -> None:
    result = {**VALID_RESULT, "status": "PASS"}
    transcript = _transcript(_event(0, "response_started"))
    out = evaluate_invariants(
        {"expected_invariants": {"terminal_state_present": True}},
        result,
        transcript,
    )
    assert out[0]["passed"] is False


def test_terminal_state_present_via_response_completed() -> None:
    transcript = _transcript(
        _event(0, "response_started"),
        _event(1, "response_completed", {"status": "completed"}),
    )
    out = evaluate_invariants(
        {"expected_invariants": {"terminal_state_present": True}},
        VALID_RESULT,
        transcript,
    )
    assert out[0]["passed"] is True


def test_expected_tool_name_positive() -> None:
    transcript = _transcript(
        _event(0, "response_started"),
        _event(1, "tool_call_completed", {"name": "get_weather", "arguments": {"city": "Paris"}}),
        _event(2, "response_completed", {"status": "completed"}),
    )
    out = evaluate_invariants(
        {"expected_invariants": {"expected_tool_name": "get_weather"}},
        VALID_RESULT,
        transcript,
    )
    assert out[0]["passed"] is True


def test_expected_tool_name_negative() -> None:
    transcript = _transcript(
        _event(0, "response_started"),
        _event(1, "tool_call_completed", {"name": "other_tool", "arguments": {}}),
        _event(2, "response_completed", {"status": "completed"}),
    )
    out = evaluate_invariants(
        {"expected_invariants": {"expected_tool_name": "get_weather"}},
        VALID_RESULT,
        transcript,
    )
    assert out[0]["passed"] is False


def test_tool_call_count() -> None:
    transcript = _transcript(
        _event(0, "response_started"),
        _event(1, "tool_call_completed", {"name": "a"}),
        _event(2, "tool_call_completed", {"name": "b"}),
        _event(3, "response_completed", {"status": "completed"}),
    )
    out = evaluate_invariants(
        {"expected_invariants": {"tool_call_count": 2}},
        VALID_RESULT,
        transcript,
    )
    assert out[0]["passed"] is True

    out_fail = evaluate_invariants(
        {"expected_invariants": {"tool_call_count": 1}},
        VALID_RESULT,
        transcript,
    )
    assert out_fail[0]["passed"] is False


def test_unknown_key_manual_review() -> None:
    out = evaluate_invariants(
        {"expected_invariants": {"usage_presence_recorded": True}},
        VALID_RESULT,
        VALID_TRANSCRIPT,
    )
    assert out[0]["name"] == "usage_presence_recorded"
    assert out[0]["passed"] is None
    assert out[0]["mode"] == "manual_review"
    assert out[0]["detail"] == "pending evaluator"


def test_evaluate_invariants_gen001_like_minimal() -> None:
    fixture = _gen001_fixture()
    transcript = _transcript(
        _event(0, "response_started"),
        _event(1, "text_delta", {"text": "Hello!"}),
        _event(2, "response_completed", {"status": "completed"}),
    )
    result = {
        **VALID_RESULT,
        "fixture_id": "GEN-001",
        "observed_terminal_state": {
            "native": "completed",
            "category": "completed",
            "source": "provider_native",
        },
    }
    out = evaluate_invariants(fixture, result, transcript)
    assert len(out) == 2
    by_name = {item["name"]: item for item in out}
    assert by_name["non_empty_assistant_content"]["passed"] is True
    assert by_name["terminal_state_present"]["passed"] is True
    assert all(item["mode"] == "deterministic" for item in out)
