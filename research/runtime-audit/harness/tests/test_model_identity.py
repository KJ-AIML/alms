"""P0.6D: cross-lane model identity provenance on the result record (finding N-05).

result.observed_model_identity distinguishes the requested model (request-side config) from the
observed returned model (a response-side observation), with a central-vocabulary source, an
auditable raw reference, the execution mode, and an EXACT-STRING match flag. No fabrication (a
missing returned model never falls back to the requested model), no canonicalization (aliases /
snapshots / families are never resolved), and a mismatch is recorded, never turned into an error.
Everything is derived offline from the raw artifact; no live provider request is made.
"""

from __future__ import annotations

from alms_audit import provenance
from alms_audit.normalizers import anthropic as anthropic_nz
from alms_audit.normalizers import gemini as gemini_nz
from alms_audit.normalizers import langchain as langchain_nz
from alms_audit.normalizers import litellm as litellm_nz
from alms_audit.normalizers import openai as openai_nz
from alms_audit.normalizers import pydanticai as pydanticai_nz
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid

_ROOT = default_root()
_RAW_REF = "raw/response.json"


def _identity(raw_obj, normalizer, *, requested_model="req-model", execution_mode="offline_mock"):
    out = interpret(
        capture_kind="response",
        raw_obj=raw_obj,
        run_id="r",
        fixture_id="F",
        lane_id="L",
        raw_manifest_ref="m.json",
        response_ref=_RAW_REF,
        normalized_ref="n.json",
        pricing=None,
        root=_ROOT,
        normalizer=normalizer,
        requested_model=requested_model,
        execution_mode=execution_mode,
    )
    assert is_valid("result", out.result)
    return out


# --- lane raw-shape builders (native returned model lives in the native container) ---
def _openai(model, status="completed"):
    obj = {
        "status": status,
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}],
    }
    if model is not None:
        obj["model"] = model
    return obj


def _anthropic(model):
    msg = {
        "role": "assistant",
        "content": [{"type": "text", "text": "x"}],
        "stop_reason": "end_turn",
    }
    if model is not None:
        msg["model"] = model
    return {"message": msg, "structured": None}


def _gemini(model, output_text=None):
    interaction = {
        "status": "completed",
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": "x"}]}],
    }
    if model is not None:
        interaction["model"] = model
    obj = {"interaction": interaction}
    if output_text is not None:
        obj["output_text"] = output_text  # SDK convenience projection; must NOT be the authority
    return obj


def _langchain(model_name):
    meta = {"finish_reason": "stop"}
    if model_name is not None:
        meta["model_name"] = model_name
    return {"message": {"content": "hi", "response_metadata": meta}}


def _litellm(model):
    resp = {"object": "chat.completion", "choices": [{"finish_reason": "stop", "message": {}}]}
    if model is not None:
        resp["model"] = model
    return {"capture_kind": "response", "response": resp}


# --- shared contract ------------------------------------------------------------------
def test_requested_and_observed_are_separate_fields():
    mi = _identity(_openai("served-x"), openai_nz, requested_model="req-y").result[
        "observed_model_identity"
    ]
    assert mi["requested_model"] == "req-y"
    assert mi["observed_returned_model"] == "served-x"
    assert mi["requested_model"] != mi["observed_returned_model"]


def test_observed_is_optional_and_unavailable_when_absent():
    mi = _identity(_openai(None), openai_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] is None
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE
    assert mi["observed_returned_model_raw_ref"] is None
    assert mi["model_identity_match"] == "unknown"


def test_observed_source_uses_central_provenance_enum():
    mi = _identity(_openai("m"), openai_nz).result["observed_model_identity"]
    assert mi["observed_returned_model_source"] in provenance.MODEL_IDENTITY_SOURCES
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED  # offline


def test_observed_present_requires_raw_ref():
    base = _identity(_openai("m"), openai_nz).result
    assert base["observed_model_identity"]["observed_returned_model_raw_ref"] == _RAW_REF
    # Schema invariant: a populated observed value without a raw_ref is INVALID.
    bad = {
        "spec": "alms.dev/runtime-audit-result/v0",
        "run_id": "r",
        "fixture_id": "F",
        "lane_id": "L",
        "status": "PASS",
        "raw_manifest": "m.json",
        "observed_model_identity": {
            "requested_model": "req",
            "observed_returned_model": "served",
            "observed_returned_model_source": provenance.FIXTURE_EXPECTED,
            "observed_returned_model_raw_ref": None,
            "execution_mode": "offline_mock",
            "model_identity_match": "false",
        },
    }
    assert not is_valid("result", bad)


def test_legacy_result_without_identity_still_validates():
    legacy = {
        "spec": "alms.dev/runtime-audit-result/v0",
        "run_id": "r",
        "fixture_id": "F",
        "lane_id": "L",
        "status": "PASS",
        "raw_manifest": "m.json",
    }
    assert is_valid("result", legacy)  # additive field never made old evidence invalid


def test_new_result_with_identity_validates():
    assert is_valid("result", _identity(_openai("m"), openai_nz).result)


def test_unknown_source_value_is_rejected():
    bad = {
        "spec": "alms.dev/runtime-audit-result/v0",
        "run_id": "r",
        "fixture_id": "F",
        "lane_id": "L",
        "status": "PASS",
        "raw_manifest": "m.json",
        "observed_model_identity": {
            "observed_returned_model": "m",
            "observed_returned_model_source": "totally_made_up",
            "observed_returned_model_raw_ref": "raw/x.json",
            "model_identity_match": "unknown",
        },
    }
    assert not is_valid("result", bad)


# --- no fabrication -------------------------------------------------------------------
def test_missing_returned_never_falls_back_to_requested():
    mi = _identity(_openai(None), openai_nz, requested_model="req").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] is None  # NOT "req"


def test_requested_and_observed_never_overwrite_each_other():
    mi = _identity(_openai("obs"), openai_nz, requested_model="req").result[
        "observed_model_identity"
    ]
    assert (mi["requested_model"], mi["observed_returned_model"]) == ("req", "obs")


def test_shared_result_builder_has_no_provider_specific_model_path():
    # The shared builder must delegate to the lane normalizer, never read a provider container.
    src = (_ROOT / "harness" / "src" / "alms_audit" / "results.py").read_text(encoding="utf-8")
    for provider_token in (
        "interaction",
        "response_metadata",
        "usage_metadata",
        "input_tokens_details",
    ):
        assert provider_token not in src


def test_no_alias_normalization_exact_strings_preserved():
    mi = _identity(_openai("GPT-4O"), openai_nz, requested_model="gpt-4o").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] == "GPT-4O"  # case preserved, not lowercased
    assert mi["model_identity_match"] == "false"  # not treated as equal


def test_no_snapshot_stripping():
    mi = _identity(_openai("gpt-4o-2024-08-06"), openai_nz, requested_model="gpt-4o").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] == "gpt-4o-2024-08-06"  # date kept
    assert mi["model_identity_match"] == "false"


def test_no_family_matching():
    mi = _identity(_openai("gpt-4o-mini"), openai_nz, requested_model="gpt-4o").result[
        "observed_model_identity"
    ]
    assert mi["model_identity_match"] == "false"  # family resemblance is not equality


# --- OpenAI native --------------------------------------------------------------------
def test_openai_offline_returned_preserved_and_fixture_expected():
    mi = _identity(_openai("gpt-served-1"), openai_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] == "gpt-served-1"
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED
    assert mi["observed_returned_model_raw_ref"] == _RAW_REF
    assert mi["execution_mode"] == "offline_mock"


def test_openai_missing_response_model_unavailable():
    mi = _identity(_openai(None), openai_nz).result["observed_model_identity"]
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


def test_openai_stream_model_read_from_completed_event():
    events = [
        {
            "sequence": 0,
            "type": "response.created",
            "data": {"type": "response.created", "response": {"model": "gpt-stream-x"}},
        },
        {
            "sequence": 1,
            "type": "response.completed",
            "data": {
                "type": "response.completed",
                "response": {"model": "gpt-stream-x", "usage": None},
            },
        },
    ]
    assert openai_nz.extract_model_identity("stream", events) == "gpt-stream-x"


# --- Anthropic native -----------------------------------------------------------------
def test_anthropic_message_model_preserved_and_fixture_expected():
    mi = _identity(_anthropic("claude-served-1"), anthropic_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] == "claude-served-1"
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED
    assert mi["observed_returned_model_raw_ref"] == _RAW_REF


def test_anthropic_missing_model_unavailable():
    mi = _identity(_anthropic(None), anthropic_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] is None
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


def test_anthropic_stream_model_from_message_start():
    env = {
        "events": [
            {
                "sequence": 0,
                "event": {"type": "message_start", "message": {"model": "claude-stream-x"}},
            }
        ]
    }
    assert anthropic_nz.extract_model_identity("stream", env) == "claude-stream-x"


# --- Gemini native --------------------------------------------------------------------
def test_gemini_interaction_model_preserved_not_convenience():
    # The Interaction resource model is authoritative; output_text convenience must be ignored.
    mi = _identity(_gemini("gemini-served-1", output_text="gemini-CONVENIENCE"), gemini_nz).result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] == "gemini-served-1"
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED


def test_gemini_missing_model_unavailable():
    mi = _identity(_gemini(None), gemini_nz).result["observed_model_identity"]
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


def test_gemini_stream_model_from_interaction():
    env = {"reconstructed": {"model": "gemini-stream-x"}, "events": []}
    assert gemini_nz.extract_model_identity("stream", env) == "gemini-stream-x"


# --- LangChain ------------------------------------------------------------------------
def test_langchain_model_never_provider_native():
    # Even offline, a framework-exposed model is fixture_expected; its LIVE source is
    # framework_native, never provider_native (regardless of how the string looks).
    assert langchain_nz.MODEL_IDENTITY_LIVE_SOURCE == provenance.FRAMEWORK_NATIVE
    mi = _identity(_langchain("gpt-4o-like"), langchain_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] == "gpt-4o-like"
    assert mi["observed_returned_model_source"] != provenance.PROVIDER_NATIVE
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED


def test_langchain_live_metadata_is_framework_native():
    mi = _identity(_langchain("gpt-4o-like"), langchain_nz, execution_mode="live").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model_source"] == provenance.FRAMEWORK_NATIVE


def test_langchain_missing_metadata_unavailable_not_requested():
    mi = _identity(_langchain(None), langchain_nz, requested_model="req").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] is None  # requested never copied into framework metadata
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


# --- live native source ---------------------------------------------------------------
def test_live_native_source_is_provider_native():
    mi = _identity(_openai("m"), openai_nz, execution_mode="live").result["observed_model_identity"]
    assert mi["observed_returned_model_source"] == provenance.PROVIDER_NATIVE


# --- mismatch semantics ---------------------------------------------------------------
def test_mismatch_is_recorded_not_an_error():
    out = _identity(_openai("served-x"), openai_nz, requested_model="requested-y")
    mi = out.result["observed_model_identity"]
    assert mi["requested_model"] == "requested-y"
    assert mi["observed_returned_model"] == "served-x"  # both unequal strings retained
    assert mi["model_identity_match"] == "false"
    assert out.status == "PASS"  # a mismatch does NOT create ERROR/FAIL
    assert out.result["status"] not in ("ERROR_RUNTIME", "FAIL_INVARIANT")
    assert is_valid("result", out.result)


def test_langchain_stream_model_from_final_message():
    env = {"final_message": {"response_metadata": {"model_name": "lc-stream-x"}}}
    assert langchain_nz.extract_model_identity("stream", env) == "lc-stream-x"


# --- LiteLLM SDK ----------------------------------------------------------------------
def test_litellm_model_never_provider_native():
    # LiteLLM's ModelResponse.model is framework-mediated: even offline it is fixture_expected,
    # and its LIVE source is framework_native, NEVER provider_native (the OpenAI-shaped string and
    # the stripped provider prefix do not make it provider evidence).
    assert litellm_nz.MODEL_IDENTITY_LIVE_SOURCE == provenance.FRAMEWORK_NATIVE
    mi = _identity(_litellm("gpt-4o-like"), litellm_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] == "gpt-4o-like"
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED  # offline
    assert mi["observed_returned_model_source"] != provenance.PROVIDER_NATIVE


def test_litellm_live_model_is_framework_native():
    mi = _identity(_litellm("gpt-4o-like"), litellm_nz, execution_mode="live").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model_source"] == provenance.FRAMEWORK_NATIVE


def test_litellm_prefix_strip_is_recorded_mismatch():
    # The classic LiteLLM canonicalization: requested openai/x, observed x -> recorded mismatch,
    # no canonicalization applied, not an error.
    out = _identity(_litellm("gpt-x"), litellm_nz, requested_model="openai/gpt-x")
    mi = out.result["observed_model_identity"]
    assert (mi["requested_model"], mi["observed_returned_model"]) == ("openai/gpt-x", "gpt-x")
    assert mi["model_identity_match"] == "false"
    assert out.status == "PASS"


def test_litellm_missing_model_unavailable_not_requested():
    mi = _identity(_litellm(None), litellm_nz, requested_model="openai/req").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] is None  # requested never copied in
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


def test_litellm_stream_model_from_aggregate():
    env = {"capture_kind": "stream", "aggregate": {"model": "gpt-stream-x"}, "chunks": []}
    assert litellm_nz.extract_model_identity("stream", env) == "gpt-stream-x"


# --- PydanticAI Agent -----------------------------------------------------------------
def _pydanticai(model):
    env = {"capture_kind": "response", "agent_run_usage": {"input_tokens": 1, "output_tokens": 1}}
    if model is not None:
        env["model_name"] = model
    return env


def test_pydanticai_model_never_provider_native():
    # PydanticAI's ModelResponse.model_name is framework-exposed: even offline it is
    # fixture_expected, and its LIVE source is framework_native, NEVER provider_native.
    assert pydanticai_nz.MODEL_IDENTITY_LIVE_SOURCE == provenance.FRAMEWORK_NATIVE
    mi = _identity(_pydanticai("gpt-4o-like"), pydanticai_nz).result["observed_model_identity"]
    assert mi["observed_returned_model"] == "gpt-4o-like"
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED  # offline
    assert mi["observed_returned_model_source"] != provenance.PROVIDER_NATIVE


def test_pydanticai_live_model_is_framework_native():
    mi = _identity(_pydanticai("gpt-4o-like"), pydanticai_nz, execution_mode="live").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model_source"] == provenance.FRAMEWORK_NATIVE


def test_pydanticai_synthetic_mismatch_recorded_not_error():
    # The offline FunctionModel exposes a synthetic model_name distinct from the requested model:
    # requested != observed is recorded (match=false), non-failing, no canonicalization.
    out = _identity(
        _pydanticai("function:offline-synthetic-model"),
        pydanticai_nz,
        requested_model="openai:gpt-4o",
    )
    mi = out.result["observed_model_identity"]
    assert (mi["requested_model"], mi["observed_returned_model"]) == (
        "openai:gpt-4o",
        "function:offline-synthetic-model",
    )
    assert mi["model_identity_match"] == "false"
    # A mismatch is non-failing (PydanticAI always carries framework_extension graph metadata).
    assert out.status in ("PASS", "PASS_WITH_EXTENSION")
    assert out.result["status"] not in ("ERROR_RUNTIME", "FAIL_INVARIANT")


def test_pydanticai_missing_model_unavailable_not_requested():
    mi = _identity(_pydanticai(None), pydanticai_nz, requested_model="req").result[
        "observed_model_identity"
    ]
    assert mi["observed_returned_model"] is None  # requested never copied into framework metadata
    assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE
