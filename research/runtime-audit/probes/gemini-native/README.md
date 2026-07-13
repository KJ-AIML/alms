# Gemini Native Probe (ALMS Phase 0)

Research/audit infrastructure ONLY. This is not the future ALMS runtime.

Isolated probe for the `gemini-native` lane. It runs fixtures through Gemini's **Interactions
API** (`google.genai` `client.interactions.create`) and preserves Interactions-native concepts
(Interaction resource, chronological steps, response_format, native stream events) to challenge
OpenAI-shaped assumptions (DevSpec Section 51). It implements Probe Process Protocol v0 (DevSpec
Section 23): one JSON request in, one JSON probe-response manifest on stdout, raw native
artifacts on disk, logs on stderr, deterministic exit codes. No `google-genai` object crosses
the process boundary — only serialized JSON does.

## Isolation

`google-genai` is a dependency of THIS probe only. It is absent from `alms/pyproject.toml`, the
harness, and the other probes. The harness cannot import `google.genai`.

## Pinned version (checked 2026-07-13)

- `google-genai==2.11.0`; pinned in `uv.lock`. Python `>=3.13`.
- The Gemini Interactions API is **Generally Available** (since June 2026) and recommended by
  Google for new projects. In google-genai 2.11.0 it is exposed through `google.genai.interactions`;
  the public module re-exports generated types and resources implemented under internal `_gaos`
  modules — an SDK implementation detail, not the API lifecycle. The "Agents usage is
  experimental" warning is agent-specific (fires only from `client.agents`) and does not apply to
  model Interaction requests. Implementation risk: `client.interactions.create` and its generated
  request types must be revalidated when google-genai is upgraded. Offline evidence uses
  schema-validated native dictionaries with the SDK's real field names.

## Native semantics preserved (not reshaped to OpenAI)

- The system instruction is a TOP-LEVEL `system_instruction`, never a user-input message.
- Input is a list of chronological steps (a `user_input` step with ordered content parts).
- The authoritative response is the full Interaction resource (`id` / `status` / `steps` /
  `usage`); `output_text` is kept separately as an SDK convenience projection.
- Structured output (STR-001) uses the native `response_format`
  (`{"text": {"mime_type": "application/json", "jsonSchema": <raw fixture schema>}}`), NOT a
  synthetic function tool. Outcomes are classified distinctly (schema pass/fail, parse-fail,
  interaction incomplete).
- Function calling (TOOL-001) uses a native function tool; the `function_call` step keeps its
  id / name / arguments and yields `requires_action`. Only the first function-call step is
  captured; no function result is submitted (no second turn).
- Native streaming lifecycle (`interaction.created` / `step.start` / `step.delta` /
  `step.stop` / `interaction.completed`) is preserved in order, including `text_delta`,
  `arguments_delta`, and `thought_signature_delta` subtypes and unknown native events.

## Storage and privacy

`store=false` is set on **every** request (no server-side retention). `previous_interaction_id`
is never used; each base fixture is stateless single-turn. Thought steps / thought-signature
deltas are preserved only as opaque structural evidence — no hidden reasoning text is requested,
normalized, or reported.

## Retry, timeout, and provider boundary

All automatic retries disabled: `HttpOptions(retry_options=HttpRetryOptions(attempts=1))` (one
attempt / zero retries); timeout is owned by `HttpOptions.timeout`. Direct Gemini only — not
Vertex, no ADC, no OpenRouter, no OpenAI-compat endpoint, no custom `base_url`. Only a direct
`GEMINI_API_KEY` can satisfy the (fail-closed, not exercised this session) live credential gate;
`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, and `GOOGLE_APPLICATION_CREDENTIALS` do not.

## Run

```
uv sync --frozen
uv run --project probes/gemini-native python -m probe <request.json>
```

Offline mock mode (no network, no credential) is selected by the harness via
`controls.mock_mode`; a socket tripwire (`ALMS_PROBE_BLOCK_NETWORK=1`) hard-blocks any outbound
connection in that mode.
