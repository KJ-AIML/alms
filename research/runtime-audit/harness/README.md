# alms-audit harness

Internal research tooling for the ALMS Phase 0 Runtime Audit Lab.
**Audit infrastructure only — not the ALMS runtime, not the public `alms` CLI.**

## Isolation

Per DevSpec Section 20 and Section 25 the harness may use general utilities (JSON Schema validation,
stdlib TOML) but must **not** depend on any runtime SDK (openai, anthropic,
google-genai, langchain, litellm, pydantic-ai, mirascope). Each runtime probe will
carry its own isolated project + lockfile under `../probes/<lane>/` (P0.4+). There is
no network code in this package.

## Setup

```bash
cd research/runtime-audit/harness
uv sync
```

## Commands (P0.1)

```bash
uv run alms-audit validate        # schemas well-formed + all fixtures valid + lanes sane
uv run alms-audit list-fixtures   # id / feature / summary
uv run alms-audit list-lanes      # lane_id / runtime_layer / provider
```

`--root PATH` points the CLI at an alternate `runtime-audit/` directory (used by the
Windows-path-with-spaces test). Later slices add `plan`, `run`, `normalize`,
`evaluate`, `summarize`, `verify-evidence` (DevSpec Section 38).

## Tests

```bash
uv run pytest
```
