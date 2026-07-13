"""P0.6C: cross-lane usage neutrality + provenance.

These lock in the hardening for findings N-01 (framework-normalized usage was labelled
provider-reported) and N-02 (non-OpenAI cache/reasoning tokens were dropped by an OpenAI-shaped
result summary). Each lane's neutral usage summary must preserve its own native cache/reasoning
shape and carry an honest `source`.
"""

from __future__ import annotations

from alms_audit.normalizers import anthropic as anthropic_nz
from alms_audit.normalizers import gemini as gemini_nz
from alms_audit.normalizers import langchain as langchain_nz
from alms_audit.normalizers import openai as openai_nz
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid


def _interp(capture_kind, raw_obj, normalizer):
    return interpret(
        capture_kind=capture_kind,
        raw_obj=raw_obj,
        run_id="r",
        fixture_id="F",
        lane_id="L",
        raw_manifest_ref="m.json",
        response_ref="raw/x.json",
        normalized_ref="n.json",
        pricing=None,
        root=default_root(),
        normalizer=normalizer,
    )


# --- OpenAI: provider-native; cache_read from input_tokens_details, reasoning from output ---


def test_openai_usage_is_provider_native_with_cache_and_reasoning():
    resp = {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "input_tokens_details": {"cached_tokens": 40},
            "output_tokens_details": {"reasoning_tokens": 8},
        },
    }
    u = _interp("response", resp, openai_nz).result["usage"]
    assert u["source"] == "provider_native"
    assert u["cache_read_input_tokens"] == 40
    assert u["cached_input_tokens"] == 40  # back-compat alias
    assert u["cache_creation_input_tokens"] is None  # not invented
    assert u["reasoning_tokens"] == 8


# --- Anthropic: the N-02 regression. cache_creation AND cache_read must survive ---


def test_anthropic_cache_split_survives_into_result_summary():
    env = {
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "x"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 50,
                "output_tokens": 10,
                "cache_creation_input_tokens": 20,
                "cache_read_input_tokens": 5,
            },
        },
        "structured": None,
    }
    u = _interp("response", env, anthropic_nz).result["usage"]
    assert u["source"] == "provider_native"
    # Both halves of Anthropic's cache split are preserved, not dropped to null (N-02).
    assert u["cache_creation_input_tokens"] == 20
    assert u["cache_read_input_tokens"] == 5
    assert u["cached_input_tokens"] == 5  # back-compat alias == cache_read
    assert u["total_tokens"] is None  # Anthropic reports no total: stays null, not fabricated
    assert u["reasoning_tokens"] is None


# --- Gemini: provider-native; thought -> reasoning (documented), cache read preserved ---


def test_gemini_thought_and_cache_tokens_preserved():
    env = {
        "interaction": {
            "status": "completed",
            "steps": [{"type": "model_output", "content": [{"type": "text", "text": "x"}]}],
            "usage": {
                "total_input_tokens": 30,
                "total_output_tokens": 12,
                "total_tokens": 42,
                "total_cached_tokens": 7,
                "total_thought_tokens": 9,
            },
        }
    }
    u = _interp("response", env, gemini_nz).result["usage"]
    assert u["source"] == "provider_native"
    assert u["cache_read_input_tokens"] == 7
    assert u["reasoning_tokens"] == 9  # Gemini thought tokens, mapped (documented normalization)


# --- LangChain: the N-01 regression. framework usage must be framework_native ---


def test_langchain_usage_is_framework_native_not_provider():
    env = {
        "message": {
            "content": "x",
            "usage_metadata": {
                "input_tokens": 11,
                "output_tokens": 3,
                "total_tokens": 14,
                "input_token_details": {"cache_read": 4},
                "output_token_details": {"reasoning": 2},
            },
            "response_metadata": {"finish_reason": "stop"},
        }
    }
    u = _interp("response", env, langchain_nz).result["usage"]
    # The core N-01 guarantee: framework-normalized usage is NOT labelled provider-native.
    assert u["source"] == "framework_native"
    assert u["cache_read_input_tokens"] == 4
    assert u["reasoning_tokens"] == 2


# --- Missing usage: null + absent + unavailable, never zero (all lanes share this path) ---


def test_missing_usage_is_absent_and_unavailable_never_zero():
    env = {
        "message": {"role": "assistant", "content": [{"type": "text", "text": "x"}], "usage": None}
    }
    u = _interp("response", env, anthropic_nz).result["usage"]
    assert u["provenance"] == "absent"
    assert u["source"] == "unavailable"
    assert u["input_tokens"] is None and u["output_tokens"] is None
    assert u["cache_read_input_tokens"] is None and u["cache_creation_input_tokens"] is None


def test_result_usage_still_schema_valid_with_new_fields():
    resp = {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}],
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    }
    assert is_valid("result", _interp("response", resp, openai_nz).result)
