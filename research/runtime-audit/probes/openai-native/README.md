# openai-native probe

ALMS Phase 0 audit probe for the **OpenAI Responses API**. Research/audit infrastructure
only. It implements Probe Process Protocol v0 (DevSpec Section 23), which is **not** the
future ModelRuntime contract. The OpenAI SDK exists only in this isolated environment; the
central harness never imports it.

## SDK and API surface

- SDK: `openai==2.45.0` (latest at selection; requires-python >=3.9).
- Native surface: `client.responses.create(...)` (Responses API) with `input` /
  `instructions`, `max_output_tokens`, `temperature`, `text.format` (json_schema) for
  structured output, flattened `function` tools + `tool_choice`, and `stream=True`.
- Streaming event types preserved as-returned: `response.created`,
  `response.output_text.delta` / `.done`, `response.function_call_arguments.delta` /
  `.done`, `response.refusal.delta`, `response.completed`, `error`, plus any unknown event.

Chat Completions is intentionally not used; Responses is the current native interface.

## Setup and tests (offline)

```bash
cd research/runtime-audit/probes/openai-native
uv sync --frozen
uv run pytest          # all offline; a network tripwire fails any accidental socket use
uv run ruff check .
```

## Run through the subprocess protocol

```bash
python -m probe <request.json>
```

Exit codes: 0 success (including a captured provider error result), 2 invalid/unknown
request, 3 blocked (BLOCKED_CONFIGURATION when no model, BLOCKED_CREDENTIAL when no
credential in live mode). With `controls.mock_mode = true` the probe runs fully offline
against a narrow deterministic fake and makes no network call.

## Live path

The live path (`build_live_client` -> real `openai.OpenAI`) is present but fail-closed and
was **not exercised** in the P0.4 offline session. A real request requires all harness
gates (`--live --confirm-live`, valid budget, call cap, live-eligible fixture, selected
lane, explicit model, credential present) plus separate explicit approval. Even when
`OPENAI_API_KEY` is present, tests and session commands do not make a provider request.

## Boundaries

Does not import production ALMS code. Does not expose OpenAI SDK objects across the process
boundary (raw evidence is serialized JSON). Does not implement a general provider
abstraction or `ModelRuntime`. Normalization into audit vocabulary is a harness stage
(`alms_audit.normalizers.openai`).
