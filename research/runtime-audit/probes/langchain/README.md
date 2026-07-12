# LangChain Compatibility Probe (ALMS Phase 0)

Research/audit infrastructure ONLY. This is not the future ALMS runtime.

Isolated probe for the `langchain-openai` lane. It runs the same control provider/model as the
`openai-native` lane through LangChain (`langchain_openai.ChatOpenAI`) so the audit can see what
the framework layer preserves, transforms, synthesizes, retries, hides, or normalizes at the
boundary (DevSpec Section 48). It implements Probe Process Protocol v0 (DevSpec Section 23):
one JSON request in, one JSON probe-response manifest on stdout, raw artifacts on disk, logs on
stderr, deterministic exit codes. LangChain objects never cross the process boundary — only
serialized JSON does.

## Isolation

LangChain is a dependency of THIS probe only. It is absent from `alms/pyproject.toml`, the
harness, and the `openai-native` probe. The harness cannot import `langchain*`.

## Pinned versions (checked 2026-07-13)

- `langchain-openai==1.3.5` (released 2026-07-10)
- `langchain-core==1.4.9` (transitive, pinned in `uv.lock`)
- `openai==2.45.0` (transitive — identical to the `openai-native` probe's direct SDK, so the
  only deliberate difference between the two lanes is the framework layer)

Python `>=3.13`.

## Retry policy

All automatic retries are disabled and each owner is recorded independently
(`build_chat_model` sets `ChatOpenAI(max_retries=0)`, which also configures the underlying
`openai` client to `max_retries=0`; no LangChain `.with_retry()` runnable is applied). The
probe records the effective retry configuration it can introspect; it never claims retries are
zero merely because the fixture requested zero.

## Provider boundary

Direct OpenAI only. No OpenRouter, no gateway, no custom `base_url`. Only a direct
`OPENAI_API_KEY` can satisfy the (fail-closed, not exercised this session) live credential gate;
`OPENROUTER_API_KEY` does not.

## Run

```
uv sync --frozen
uv run --project probes/langchain python -m probe <request.json>
```

Offline mock mode (no network, no credential) is selected by the harness via
`controls.mock_mode`; a socket tripwire (`ALMS_PROBE_BLOCK_NETWORK=1`) hard-blocks any outbound
connection in that mode.
