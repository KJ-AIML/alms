"""Deterministic invariant evaluators (DevSpec Section 44, P0-020)."""

from __future__ import annotations

import json
from typing import Any

_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "reasoning_tokens",
)

_STREAM_EVENT_TYPES = frozenset(
    {
        "text_delta",
        "tool_call_arguments_delta",
    }
)


def _events(transcript: dict | None) -> list[dict]:
    if not transcript:
        return []
    events = transcript.get("events")
    return events if isinstance(events, list) else []


def _usage_token_values(usage: dict) -> list[Any]:
    return [usage.get(field) for field in _TOKEN_FIELDS]


def _has_token_values(usage: dict) -> bool:
    return any(value is not None for value in _usage_token_values(usage))


def _parse_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _subset_equal(actual: Any, expected: dict) -> bool:
    if not isinstance(actual, dict):
        return False
    for key, expected_value in expected.items():
        if key not in actual:
            return False
        if actual[key] != expected_value:
            return False
    return True


def _structured_parsed(transcript: dict | None) -> Any:
    for event in _events(transcript):
        if event.get("type") != "structured_output_completed":
            continue
        data = event.get("data") or {}
        parsed = data.get("parsed")
        if parsed is not None:
            return parsed
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            loaded = _parse_json_value(text)
            if isinstance(loaded, dict):
                return loaded
    return None


def _tool_calls(transcript: dict | None) -> list[dict]:
    return [e for e in _events(transcript) if e.get("type") == "tool_call_completed"]


def _deferred_tool_names(transcript: dict | None) -> list[str]:
    names: list[str] = []
    for event in _events(transcript):
        if event.get("type") != "framework_extension":
            continue
        data = event.get("data") or {}
        if data.get("native_type") != "pydanticai_deferred_tool_requests":
            continue
        for approval in data.get("approvals") or []:
            name = approval.get("tool_name")
            if isinstance(name, str) and name:
                names.append(name)
        for call in data.get("calls") or []:
            name = call.get("name") or call.get("tool_name")
            if isinstance(name, str) and name:
                names.append(name)
    return names


def _is_error_fixture(fixture: dict) -> bool:
    fixture_id = fixture.get("id", "")
    return fixture.get("feature") == "errors" or (
        isinstance(fixture_id, str) and fixture_id.startswith("ERROR-")
    )


def _is_str_fixture(fixture: dict) -> bool:
    fixture_id = fixture.get("id", "")
    return isinstance(fixture_id, str) and fixture_id.startswith("STR-")


def evaluate_usage_not_fabricated(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, transcript, expected
    usage = result.get("usage")
    if not isinstance(usage, dict):
        return True, "no usage block on result", "deterministic"

    provenance = usage.get("provenance")
    has_tokens = _has_token_values(usage)

    if provenance == "absent":
        if has_tokens:
            return (
                False,
                "provenance is absent but token fields are populated "
                "(missing must stay null, not 0)",
                "deterministic",
            )
        return True, "absent provenance with all token fields null", "deterministic"

    if has_tokens:
        return True, f"token values present with provenance={provenance!r}", "deterministic"

    return True, "no token values recorded", "deterministic"


def evaluate_terminal_state_present(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, expected
    status = result.get("status", "")
    if isinstance(status, str) and status.startswith(("ERROR_", "BLOCKED_", "UNSUPPORTED_")):
        return True, f"terminal signal implied by status {status}", "deterministic"

    if result.get("observed_terminal_state") is not None:
        return True, "observed_terminal_state present on result", "deterministic"

    if any(e.get("type") == "response_completed" for e in _events(transcript)):
        return True, "response_completed event in transcript", "deterministic"

    return (
        False,
        "no observed_terminal_state, response_completed, or exempt status",
        "deterministic",
    )


def evaluate_non_empty_assistant_content(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, expected
    status = result.get("status", "")
    if isinstance(status, str) and (
        status.startswith(("ERROR_", "BLOCKED_", "UNSUPPORTED_"))
        or status in ("FAIL_INVARIANT", "INCONCLUSIVE")
    ):
        return True, f"content not required for status {status}", "deterministic"

    for event in _events(transcript):
        etype = event.get("type")
        data = event.get("data") or {}
        if etype == "text_delta":
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                return True, "non-empty text_delta in transcript", "deterministic"
        if etype == "structured_output_completed":
            parsed = data.get("parsed")
            if parsed is not None and parsed != {}:
                return True, "structured_output_completed with parsed content", "deterministic"
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                return True, "structured_output_completed with non-empty text", "deterministic"

    return False, "no non-empty assistant content in transcript", "deterministic"


def evaluate_expected_tool_name(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, result
    if not isinstance(expected, str) or not expected:
        return True, "no expected tool name constraint", "deterministic"

    for call in _tool_calls(transcript):
        data = call.get("data") or {}
        if data.get("name") == expected:
            return True, f"tool_call_completed name matches {expected!r}", "deterministic"

    for name in _deferred_tool_names(transcript):
        if name == expected:
            return True, f"deferred tool request matches {expected!r}", "deterministic"

    for event in _events(transcript):
        if event.get("type") != "provider_extension":
            continue
        data = event.get("data") or {}
        if data.get("native_type") == "requires_action":
            for step in data.get("steps") or []:
                if step.get("name") == expected:
                    return True, f"requires_action extension lists {expected!r}", "deterministic"

    return False, f"no tool_call_completed or deferred request named {expected!r}", "deterministic"


def evaluate_expected_tool_arguments(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, result
    if not isinstance(expected, dict) or not expected:
        return True, "no expected tool arguments constraint", "deterministic"

    for call in _tool_calls(transcript):
        data = call.get("data") or {}
        args = _parse_json_value(data.get("arguments"))
        if _subset_equal(args, expected):
            return True, "tool arguments match expected subset", "deterministic"

    return False, "no tool_call_completed arguments match expected subset", "deterministic"


def evaluate_tool_call_count(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, result
    if not isinstance(expected, int):
        return True, "no tool_call_count constraint", "deterministic"

    completed = _tool_calls(transcript)
    deferred_extra = 0
    for event in _events(transcript):
        if event.get("type") != "framework_extension":
            continue
        data = event.get("data") or {}
        if data.get("native_type") == "pydanticai_deferred_tool_requests":
            approvals = data.get("approvals") or []
            calls = data.get("calls") or []
            deferred_extra = max(0, len(approvals) + len(calls) - len(completed))

    count = len(completed) + deferred_extra
    if count == expected:
        return True, f"tool call count {count} equals expected {expected}", "deterministic"
    return False, f"tool call count {count} != expected {expected}", "deterministic"


def evaluate_schema_valid(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del expected
    structured_expected = fixture.get("output_schema") is not None or fixture.get(
        "expected_invariants", {}
    ).get("schema_valid")

    if not structured_expected:
        return True, "fixture does not require structured output", "deterministic"

    if any(e.get("type") == "structured_output_completed" for e in _events(transcript)):
        return True, "structured_output_completed present in transcript", "deterministic"

    notes = result.get("notes") or []
    if isinstance(notes, list) and any(
        isinstance(note, str) and "schema" in note.lower() for note in notes
    ):
        return True, "result notes reference schema", "deterministic"

    status = result.get("status", "")
    if isinstance(status, str) and status.startswith("PASS") and _is_str_fixture(fixture):
        return (
            True,
            "soft pass: PASS status on STR fixture without structured event",
            "deterministic",
        )

    return False, "structured output expected but not recorded", "deterministic"


def evaluate_expected_fields_equal(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, result
    if not isinstance(expected, dict) or not expected:
        return True, "no expected_fields_equal constraint", "deterministic"

    parsed = _structured_parsed(transcript)
    if parsed is None:
        return False, "no structured output available to compare fields", "deterministic"

    if _subset_equal(parsed, expected):
        return True, "structured output fields match expected subset", "deterministic"
    return False, f"structured output {parsed!r} does not match expected subset", "deterministic"


def evaluate_stream_has_monotonic_sequence(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del fixture, result, expected
    events = _events(transcript)
    stream_events = [e for e in events if e.get("type") in _STREAM_EVENT_TYPES]

    if stream_events:
        sequences = [e.get("sequence") for e in events if "sequence" in e]
        if sequences:
            for prev, curr in zip(sequences, sequences[1:], strict=False):
                if prev is None or curr is None:
                    continue
                if curr < prev:
                    return (
                        False,
                        f"sequence not monotonic: {prev} then {curr}",
                        "deterministic",
                    )
            return True, "event sequences are monotonic", "deterministic"

    started_idx = next(
        (i for i, e in enumerate(events) if e.get("type") == "response_started"),
        None,
    )
    completed_idx = next(
        (i for i, e in enumerate(events) if e.get("type") == "response_completed"),
        None,
    )
    if started_idx is not None and completed_idx is not None and started_idx < completed_idx:
        return True, "response_started precedes response_completed", "deterministic"

    if not stream_events and not events:
        return False, "no transcript events to evaluate stream ordering", "deterministic"

    return False, "stream sequence ordering could not be verified", "deterministic"


def evaluate_error_category_present(
    fixture: dict,
    result: dict,
    transcript: dict | None,
    expected: Any,
) -> tuple[bool | None, str, str]:
    del expected
    status = result.get("status", "")
    applies = _is_error_fixture(fixture) or status == "ERROR_RUNTIME"
    if not applies:
        return True, "error category not required for this fixture/status", "deterministic"

    if any(e.get("type") == "error" for e in _events(transcript)):
        return True, "error event present in transcript", "deterministic"

    terminal = result.get("observed_terminal_state") or {}
    category = terminal.get("category")
    if category in ("error", "refusal", "unknown") and terminal.get("native"):
        return True, f"terminal category {category!r} recorded", "deterministic"

    notes = result.get("notes") or []
    if isinstance(notes, list) and any(
        isinstance(note, str) and "error" in note.lower() for note in notes
    ):
        return True, "result notes reference error", "deterministic"

    return False, "ERROR fixture/status but no error event or category", "deterministic"
