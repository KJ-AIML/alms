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

## Commands

```bash
uv run alms-audit validate
uv run alms-audit lint-fixtures
uv run alms-audit list-fixtures
uv run alms-audit list-lanes
uv run alms-audit plan
uv run alms-audit run                 # dry-run by default
uv run alms-audit normalize --run <ID>
uv run alms-audit evaluate --run <ID>
uv run alms-audit summarize --run <ID>
uv run alms-audit verify-evidence --revision P0-E1
```

`--root PATH` points the CLI at an alternate `runtime-audit/` directory (used by the
Windows-path-with-spaces test). Post-run commands operate on recorded artifacts only and
make no provider calls (DevSpec Section 38).

## Tests

```bash
uv run pytest
```
