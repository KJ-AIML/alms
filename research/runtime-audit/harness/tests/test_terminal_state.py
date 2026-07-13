"""P0.6C: observed_terminal_state on the result record (finding N-03).

The provider/framework-native terminal signal is now queryable at the result level (a different
axis from the audit `status` verdict), read back out of the preserved transcript so it never
contradicts the evidence. Unknown natives are kept verbatim, never dropped.
"""

from __future__ import annotations

from alms_audit.normalizers import anthropic as anthropic_nz
from alms_audit.normalizers import gemini as gemini_nz
from alms_audit.normalizers import langchain as langchain_nz
from alms_audit.normalizers import openai as openai_nz
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid


def _terminal(capture_kind, raw_obj, normalizer):
    out = interpret(
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
    assert is_valid("result", out.result)
    return out.result["observed_terminal_state"]


def _openai(status):
    return {
        "status": status,
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}],
    }


def _anthropic(stop_reason, content=None):
    return {
        "message": {
            "role": "assistant",
            "content": content or [{"type": "text", "text": "x"}],
            "stop_reason": stop_reason,
        },
        "structured": None,
    }


def _gemini(status, steps=None):
    return {
        "interaction": {
            "status": status,
            "steps": steps
            or [{"type": "model_output", "content": [{"type": "text", "text": "x"}]}],
        }
    }


def test_openai_completed_is_provider_native():
    ts = _terminal("response", _openai("completed"), openai_nz)
    assert ts == {"native": "completed", "category": "completed", "source": "provider_native"}


def test_openai_incomplete_is_representable():
    ts = _terminal("response", _openai("incomplete"), openai_nz)
    assert ts["native"] == "incomplete"
    assert ts["category"] == "incomplete"


def test_anthropic_refusal_terminal_state():
    ts = _terminal("response", _anthropic("refusal"), anthropic_nz)
    assert ts["native"] == "refusal"
    assert ts["category"] == "refusal"
    assert ts["source"] == "provider_native"


def test_anthropic_max_tokens_terminal_state():
    ts = _terminal("response", _anthropic("max_tokens"), anthropic_nz)
    assert ts["category"] == "max_tokens"


def test_gemini_requires_action_is_first_class():
    steps = [{"type": "function_call", "id": "c1", "name": "f", "arguments": "{}"}]
    ts = _terminal("response", _gemini("requires_action", steps), gemini_nz)
    assert ts["native"] == "requires_action"
    assert ts["category"] == "requires_action"


def test_gemini_budget_exceeded_is_first_class():
    ts = _terminal("response", _gemini("budget_exceeded"), gemini_nz)
    assert ts["category"] == "budget_exceeded"


def test_gemini_unknown_terminal_kept_verbatim_not_dropped():
    ts = _terminal("response", _gemini("some_future_state"), gemini_nz)
    assert ts["native"] == "some_future_state"  # preserved, not discarded
    assert ts["category"] == "unknown"  # coarse bucket, no data loss


def test_langchain_terminal_state_is_framework_native():
    env = {"message": {"content": "x", "response_metadata": {"finish_reason": "stop"}}}
    ts = _terminal("response", env, langchain_nz)
    assert ts["category"] == "completed"
    assert ts["source"] == "framework_native"  # finish_reason is framework-normalized
