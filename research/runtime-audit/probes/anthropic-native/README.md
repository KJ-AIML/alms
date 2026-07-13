# Anthropic Native Probe (ALMS Phase 0)

Research/audit infrastructure ONLY. This is not the future ALMS runtime.

Isolated probe for the `anthropic-native` lane. It runs fixtures through Anthropic's direct
Messages API (`anthropic.Anthropic().messages.create`) and preserves Anthropic-native semantics
to challenge OpenAI-shaped assumptions in the audit (DevSpec Section 50). It implements Probe
Process Protocol v0 (DevSpec Section 23): one JSON request in, one JSON probe-response manifest
on stdout, raw native artifacts on disk, logs on stderr, deterministic exit codes. No Anthropic
SDK object ever crosses the process boundary — only serialized JSON does.

## Isolation

The Anthropic SDK is a dependency of THIS probe only. It is absent from `alms/pyproject.toml`,
the harness, and the other probes. The harness cannot import `anthropic`.

## Pinned versions (checked 2026-07-13)

- `anthropic==0.116.0` (released 2026-07-02); pinned in `uv.lock`.
- Python `>=3.13`. No `openai` or `langchain` package is pulled transitively.

## Native semantics preserved (not reshaped to OpenAI)

- The system instruction is a TOP-LEVEL `system` field, never an assistant/system message.
- Assistant output is an ordered list of content blocks (`text`, `tool_use`).
- `tool_use` blocks keep their native id / name / raw input; they are not converted to an
  OpenAI `function_call` in raw evidence.
- Structured output (STR-001) uses direct Messages API JSON structured output via
  `output_config.format` (`{"format": {"type": "json_schema", "schema": <raw fixture schema>}}`),
  which shapes the response. This is complementary to, and distinct from, strict tool use
  (`strict: true`, which constrains tool INPUT — see TOOL-001).
- Native streaming lifecycle (`message_start` / `content_block_start` / `content_block_delta`
  with `text_delta` and `input_json_delta` subtypes / `content_block_stop` / `message_delta` /
  `message_stop`, plus `ping`) is preserved in order.
- Usage is split across events and reports cache tokens (`cache_creation_input_tokens`,
  `cache_read_input_tokens`) natively; missing usage stays absent.

## Retry policy

All automatic retries disabled: `anthropic.Anthropic(max_retries=0)` (the SDK default is 2),
which also governs the HTTP transport. No probe/harness/subprocess retry. The probe records the
effective configuration and the calls it actually observed; it never claims zero merely because
a fixture requested zero.

## Provider boundary

Direct Anthropic only. No OpenRouter, Bedrock, Vertex, gateway, or custom `base_url`. Only a
direct `ANTHROPIC_API_KEY` can satisfy the (fail-closed, not exercised this session) live
credential gate; `OPENROUTER_API_KEY` does not.

## Run

```
uv sync --frozen
uv run --project probes/anthropic-native python -m probe <request.json>
```

Offline mock mode (no network, no credential) is selected by the harness via
`controls.mock_mode`; a socket tripwire (`ALMS_PROBE_BLOCK_NETWORK=1`) hard-blocks any outbound
connection in that mode.
