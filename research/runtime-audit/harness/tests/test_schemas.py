"""P0.1 schema contract tests: positive + negative, and the required-property invariants."""

from __future__ import annotations

import importlib.util

import pytest

from alms_audit import fixtures as fx
from alms_audit.schemas import SCHEMA_FILES, is_valid, validation_errors, validator_for

# ---- minimal valid instances ------------------------------------------------

VALID_PROBE_REQUEST = {
    "protocol_version": "alms.dev/probe-protocol/v0",
    "run_id": "r1",
    "fixture_path": "fixtures/generation/generation-basic-001.json",
    "lane": {"lane_id": "openai-native", "runtime_layer": "openai", "provider": "openai", "model": "m"},
    "output_dir": "runs/r1",
    "controls": {"timeout_ms": 30000, "max_attempts": 1},
    "redaction_mode": "strict",
}

VALID_PROBE_RESPONSE = {
    "spec": "alms.dev/probe-response/v0",
    "run_id": "r1",
    "fixture_id": "generation-basic-001",
    "fixture_hash": "sha256:abc",
    "probe_id": "openai-native",
    "probe_version": "0.0.0",
    "package_versions": {"openai": "2.0.0"},
    "provider": "openai",
    "model": "m",
    "started_at": "2026-07-12T00:00:00Z",
    "ended_at": "2026-07-12T00:00:01Z",
    "exit_code": 0,
    "stdout_path": "runs/r1/stdout.txt",
    "stderr_path": "runs/r1/stderr.txt",
    "request_path": "runs/r1/request.json",
    "response_path": "runs/r1/response.json",
    "retry_count_observed": None,
    "redaction_summary": {"mode": "strict", "fields_redacted": []},
}

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
    "fixture_id": "generation-basic-001",
    "lane_id": "openai-native",
    "status": "PASS",
    "raw_manifest": "runs/r1/raw-manifest.json",
}

VALID_FINDING = {
    "spec": "alms.dev/runtime-audit-finding/v0",
    "id": "F-001",
    "severity": "F1",
    "status": "proposed",
    "runtime_lanes": ["openai-native"],
    "fixture_ids": ["structured-person-001"],
    "assumption_id": "A-001",
    "expected_behavior": "native structured output",
    "observed_behavior": "prompt-coerced json",
    "reproduction_command": "alms-audit run --fixture structured-person-001",
    "raw_evidence_refs": [],
    "normalized_evidence_refs": [],
    "semantic_impact": "shape differs",
    "contract_implication": "structured output mode must be explicit",
    "confidence": "medium",
    "follow_up_experiment": None,
    "kj_decision": None,
}

VALID_RUN_MANIFEST = {
    "spec": "alms.dev/runtime-audit-run-manifest/v0",
    "run_id": "r1",
    "git_sha": "04624bf",
    "harness_lock_hash": "h",
    "probe_lock_hashes": {},
    "fixture_corpus_hash": "fc",
    "os": "Windows 10.0.26200",
    "python": "3.13.13",
    "selected_lanes": [],
    "selected_fixtures": [],
    "model_configuration": {},
    "credential_presence": {"OPENAI_API_KEY": True},
    "budget": {"hard_cap_usd": 0},
    "command_line": "alms-audit run",
    "started_at": "2026-07-12T00:00:00Z",
    "ended_at": None,
}


# ---- schema well-formedness -------------------------------------------------

@pytest.mark.parametrize("name", sorted(SCHEMA_FILES))
def test_schema_file_is_valid_json_schema(name: str) -> None:
    validator_for(name)  # constructs after Draft202012Validator.check_schema


# ---- fixtures: positive + negative ------------------------------------------

def test_example_fixtures_all_validate() -> None:
    loaded = fx.load_fixtures()
    assert loaded, "expected example fixtures on disk"
    for fixture in loaded:
        assert is_valid("fixture", fixture.data), validation_errors("fixture", fixture.data)


def test_fixture_missing_required_field_is_rejected() -> None:
    bad = dict(VALID_RESULT)  # wrong shape entirely for a fixture
    assert validation_errors("fixture", bad)


def test_fixture_requires_messages_or_embedding_inputs() -> None:
    bad = {
        "spec": "alms.dev/runtime-audit-fixture/v0",
        "id": "x",
        "feature": "generation",
        "summary": "no inputs",
        "requirements": {"live_required": False, "capabilities": []},
        "execution": {},
        "expected_invariants": {},
    }
    assert validation_errors("fixture", bad)


# ---- required-property invariants -------------------------------------------

def test_probe_request_and_response_valid() -> None:
    assert is_valid("probe-request", VALID_PROBE_REQUEST)
    assert is_valid("probe-response", VALID_PROBE_RESPONSE)


def test_transcript_event_requires_raw_ref() -> None:
    """Raw Evidence != Normalized Interpretation: every event must point back to raw."""
    assert is_valid("normalized-transcript", VALID_TRANSCRIPT)
    broken = {
        "spec": "alms.dev/normalized-transcript/v0",
        "raw_manifest": "runs/r1/raw-manifest.json",
        "events": [{"sequence": 0, "type": "response_started", "timestamp_relative_ms": 0, "data": {}}],
    }
    assert validation_errors("normalized-transcript", broken)


def test_result_status_enum_distinguishes_outcomes() -> None:
    """Unsupported != Failed: only the eight defined statuses are allowed."""
    assert is_valid("result", VALID_RESULT)
    assert is_valid("result", {**VALID_RESULT, "status": "UNSUPPORTED_DECLARED"})
    assert validation_errors("result", {**VALID_RESULT, "status": "OK"})


def test_result_usage_missing_is_null_not_zero() -> None:
    """Missing usage != zero usage: null token fields are valid."""
    usage = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "provenance": "absent",
        "finality": "partial",
    }
    assert is_valid("result", {**VALID_RESULT, "usage": usage})


def test_finding_severity_enum() -> None:
    assert is_valid("finding", VALID_FINDING)
    assert validation_errors("finding", {**VALID_FINDING, "severity": "F9"})


def test_run_manifest_rejects_unknown_field() -> None:
    """Manifest must never carry secret values: extra fields are rejected."""
    assert is_valid("run-manifest", VALID_RUN_MANIFEST)
    leaky = {**VALID_RUN_MANIFEST, "OPENAI_API_KEY": "sk-secret"}
    assert validation_errors("run-manifest", leaky)


# ---- isolation --------------------------------------------------------------

def _is_installed(module: str) -> bool:
    # find_spec raises ModuleNotFoundError for "a.b" when parent "a" is absent.
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


@pytest.mark.parametrize(
    "module",
    ["openai", "anthropic", "langchain", "litellm", "google.generativeai", "google.genai", "pydantic_ai", "mirascope"],
)
def test_no_runtime_sdk_dependency(module: str) -> None:
    """DevSpec Section 20 and Section 25: the harness env must not carry any runtime SDK."""
    assert not _is_installed(module), f"{module} must not be installed in the harness env"
