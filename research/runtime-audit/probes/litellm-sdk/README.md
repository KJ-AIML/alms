# litellm-sdk probe

ALMS Phase 0 Runtime Audit Lab — LiteLLM **Python SDK** abstraction stress lane.

Research/audit infrastructure only. Implements Probe Process Protocol v0 (DevSpec Section 23),
which is NOT the future ModelRuntime contract.

## Boundary: SDK, not Proxy

This lane audits the LiteLLM Python SDK (`litellm.completion`). It does **not** audit the
LiteLLM **Proxy Server**, virtual keys, gateway authentication, proxy rate limiting, proxy
database state, proxy administration APIs, router, fallbacks, load balancing, multiple
deployments, caching, telemetry callbacks, observability integrations, or spend tracking. Those
belong to a separate server-boundary slice if later justified. `fastapi` (a proxy-server
dependency) is deliberately absent; its absence is part of the boundary.

## Isolation

`litellm` lives ONLY in this probe env (DevSpec Sections 20 and 25); the central harness never
imports it. On import the probe sets `LITELLM_LOCAL_MODEL_COST_MAP=True` so `import litellm`
makes no network call (LiteLLM otherwise fetches a remote model-cost map from GitHub). Every
automatic behavior is disabled: telemetry off, success/failure/input callbacks empty, cache
None, `num_retries=0`, no Router (so no fallbacks / load balancing), no `base_url` override.

## Offline injection

Offline runs use LiteLLM's own `mock_response` seam, so real LiteLLM machinery runs — provider
routing (`get_llm_provider`), request-param translation (`get_optional_params`), `ModelResponse`
typing, `_hidden_params` attachment, and the streaming wrapper — with zero network. The probe
does not return a prebuilt response or a normalized transcript; it captures raw LiteLLM evidence
that the harness `litellm` normalizer interprets. Real provider request/response translation
stays `unverified_until_live`.

## What LiteLLM does to the evidence (measured offline)

- **Model identity**: strips the provider prefix on the returned model field (`openai/x` -> `x`);
  the full requested string survives only in `_hidden_params.litellm_model_name`. Recorded as a
  requested/observed mismatch, never corrected, never an error.
- **Usage**: presented in an OpenAI shape but LiteLLM-owned (framework_native), offline
  synthesized by `token_counter` — never provider-reported.
- **Structured output**: `response_format` json_schema is framework-mediated; valid JSON offline
  is not native-structured proof.
- **Tools**: request translation via `get_optional_params`; passing tools to `completion` routes
  through proxy MCP utilities (fastapi), so the tool-call response is injected via LiteLLM's own
  `ModelResponse` types.
- **Errors**: LiteLLM's own OpenAI-shaped exception taxonomy, never labelled provider-native.

## Run

```
uv sync --frozen
uv run pytest
uv run --project probes/litellm-sdk python -m probe <request.json>
```

No live provider request is made offline, and the LiteLLM Proxy Server is never started.
