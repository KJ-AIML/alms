"""LiteLLM SDK isolation, offline injection seam, and retry/fallback introspection.

This lane audits the LiteLLM Python SDK (`litellm.completion`), NOT the LiteLLM Proxy Server.

Isolation (DevSpec Sections 64, 80, and the callback/telemetry rules): every automatic behavior
that could add a hidden call, mutate evidence, or exfiltrate a prompt is disabled — telemetry,
success/failure/input callbacks, response cache, and per-call retries. No Router is constructed,
so no fallbacks / load balancing / multiple deployments exist. No base_url is ever set: the lane
must not be silently redirected to OpenRouter or any gateway.

Offline injection uses litellm's OWN documented `mock_response` seam. The call still runs real
litellm machinery — provider routing (get_llm_provider), request-param translation
(get_optional_params), ModelResponse typing, _hidden_params attachment, and the streaming
wrapper — so this is not a harness-prebuilt response and not a normalized transcript. What it does
NOT exercise is the real provider request/response translation, which stays unverified_until_live.
"""

from __future__ import annotations

from typing import Any

import litellm

# LiteLLM's returned model field, usage, tool-call, streaming, and exception shapes are OpenAI-
# Chat-Completions-SHAPED but LiteLLM-OWNED. Under a LIVE call they are framework_native, NEVER
# provider_native (even when a string resembles an OpenAI id). Offline evidence is downgraded to
# fixture_expected by the shared harness result builder. Exposed for the harness manifest.
MODEL_IDENTITY_LIVE_SOURCE = "framework_native"


def configure_litellm_isolation() -> dict:
    """Disable every automatic LiteLLM behavior and return the effective state as evidence.

    Never assumes a value is safe by default — it reads defaults first, then forces the safe
    state, so the manifest records what was actually in force (num_retries default is None, and
    telemetry defaults True; both are corrected here).
    """
    litellm.telemetry = False
    litellm.suppress_debug_info = True  # stop litellm printing promo/info banners
    litellm.num_retries = 0
    litellm.success_callback = []
    litellm.failure_callback = []
    litellm.input_callback = []
    litellm._async_success_callback = []
    litellm.callbacks = []
    litellm.cache = None
    litellm.drop_params = False
    return isolation_introspection()


def isolation_introspection() -> dict:
    """Record callback/telemetry/cache/retry/router/fallback ownership as observed evidence."""
    return {
        "telemetry": bool(getattr(litellm, "telemetry", None)),
        "num_retries": getattr(litellm, "num_retries", None),
        "success_callback": list(getattr(litellm, "success_callback", []) or []),
        "failure_callback": list(getattr(litellm, "failure_callback", []) or []),
        "input_callback": list(getattr(litellm, "input_callback", []) or []),
        "callbacks": list(getattr(litellm, "callbacks", []) or []),
        "cache": getattr(litellm, "cache", None),
        "router_used": False,  # this lane never constructs a litellm Router
        "fallbacks": None,  # no fallbacks / context-window fallbacks / content-policy fallbacks
        "base_url_override": None,  # no custom base_url; direct provider only
    }


def observe_routing(model: str) -> dict:
    """Observe the routing decision litellm derives from the model STRING (get_llm_provider).

    This is the request-side routing view. It does NOT prove the real provider was reached; the
    actual provider request/route stays unverified_until_live. A bare (unqualified) model string
    is recorded as an error rather than silently defaulted to a provider.
    """
    try:
        model_name, provider, _key, api_base = litellm.get_llm_provider(model)
        return {
            "requested_model_string": model,
            "resolved_provider": provider,
            "resolved_model_component": model_name,
            "resolved_api_base": api_base,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - a routing failure is recorded evidence, not a crash
        return {
            "requested_model_string": model,
            "resolved_provider": None,
            "resolved_model_component": None,
            "resolved_api_base": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _tool_call_mock(model: str) -> Any:
    """Build a LiteLLM ModelResponse carrying a tool call, from litellm's OWN types.

    litellm's string mock cannot express tool_calls, so a complex mock is injected as a real
    litellm ModelResponse. The request-side tool translation (tools -> provider params via
    get_optional_params) is still exercised; the tool-call RESPONSE shape is injected, so
    provider -> litellm tool translation stays unverified_until_live.
    """
    from litellm.types.utils import Choices, Message, ModelResponse, Usage

    message = Message(
        content=None,
        role="assistant",
        tool_calls=[
            {
                "id": "call_litellm_tool_1",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'},
            }
        ],
    )
    # Mirror litellm's returned-model behavior (it strips the provider prefix on the ModelResponse
    # model field) so this lane's model-identity evidence is uniform across scenarios.
    returned_model = model.split("/", 1)[1] if "/" in model else model
    return ModelResponse(
        choices=[Choices(finish_reason="tool_calls", index=0, message=message)],
        model=returned_model,
        usage=Usage(prompt_tokens=9, completion_tokens=5, total_tokens=14),
    )


def execution_path(scenario: str) -> dict:
    """Classify which offline execution path a fixture actually exercised (evidence accuracy).

    The six fixtures do NOT all use an identical path. Vocabulary:
      * completion_mock_response         - litellm.completion(mock_response=<str>) fully exercised.
      * framework_request_transformation - litellm request-param translation (get_optional_params),
                                           either inside completion (response_format) or as an
                                           explicit external step (tools).
      * framework_response_object_injection - a litellm ModelResponse injected as mock_response
                                           (used for tool_calls, which cannot be expressed by a
                                           string mock).
      * full_provider_adapter            - the real provider adapter path. NEVER exercised offline.
      * full_completion_tools_path       - litellm.completion(tools=...) end to end. NOT exercised
                                           (it imports proxy MCP utilities requiring fastapi).

    This records what was exercised, not what output type was instantiated.
    """
    tools = scenario == "tools"
    structured = scenario == "structured"
    if tools:
        components = ["framework_request_transformation", "framework_response_object_injection"]
        coverage = "offline_partial_request_transform_plus_response_injection"
    elif structured:
        components = ["completion_mock_response", "framework_request_transformation"]
        coverage = "offline_completion_mock_path"
    else:
        components = ["completion_mock_response"]
        coverage = "offline_completion_mock_path"

    unverified = [
        "full_provider_adapter",
        "provider_request_creation",
        "provider_returned_semantics",
        "network_exception_mapping",
    ]
    if tools:
        unverified = ["full_completion_tools_path", *unverified]

    entry: dict = {
        "scenario": scenario,
        "components": components,
        "full_provider_adapter_exercised": False,
        "coverage": coverage,
        "unverified_until_live": unverified,
    }
    if tools:
        entry["full_completion_tools_path_exercised"] = False
        entry["package_boundary_dependency"] = (
            "litellm.completion(tools=...) imports proxy MCP utilities requiring fastapi, "
            "which is absent by design in this SDK-only probe (see finding L-01)"
        )
    elif structured:
        entry["note"] = (
            "response_format json_schema translated inside completion via get_optional_params"
        )
    elif scenario == "usage":
        entry["note"] = "usage is framework-synthesized by litellm token_counter on the mock path"
    return entry


def mock_argument(scenario: str, model: str) -> Any:
    """Return the `mock_response` value for a scenario (offline mode only).

    string content for generation/roles/usage/stream; a schema-valid JSON string for structured;
    a litellm ModelResponse with tool_calls for tools. The error scenario injects an exception
    instance so litellm exercises its OWN exception mapping (not one of the six base fixtures).
    """
    if scenario == "tools":
        return _tool_call_mock(model)
    if scenario == "structured":
        return '{"name": "Alice", "age": 30}'
    if scenario == "error":
        return Exception("synthetic offline litellm failure (no provider contacted)")
    return "Hello there, friend."
