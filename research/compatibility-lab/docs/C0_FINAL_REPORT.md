# C0 Final Report

## Track

Compatibility Lab C0 — custom endpoint and gateway compatibility.

Evidence class: `custom_endpoint_compatibility`.

Custom endpoint compatibility evidence is not native-provider evidence.
It does not satisfy G2 or G3.

## Completed slices

| Slice | Result |
| --- | --- |
| C0.0 | Charter, DevSpec, roadmap, baseline |
| C0.1 | Endpoint configuration and secret-safety contract + tests |
| C0.2 | `openai-compatible-custom` offline lane (real OpenAI SDK + MockTransport) |
| C0.3 | `anthropic-compatible-custom` offline lane (real Anthropic SDK + MockTransport; SUPPORTED) |
| C0.4 | Endpoint identity and provenance decision **B** (`endpoint_boundary` additive) |
| C0.5 | Capability profiles under `reports/capabilities/` |
| C0.6 | Compatibility matrix + schema (separate from Phase 0 native matrix) |
| C0.7 | `BLOCKED_CONFIGURATION` — fresh live env vars absent |
| C0.8 | Adapter guide, security checklist, endpoint-profile schema/example |
| C0.9 | This closeout |

## Architecture

```text
compatibility harness contracts (alms_compat)
  -> isolated probe subprocess
  -> OpenAI/Anthropic SDK configured with custom base_url
  -> offline httpx.MockTransport seam (real request construction + response parsing)
  -> raw endpoint-boundary evidence
  -> compatibility normalizer (no provider_native fabrication)
```

## Security

- Authorization values redacted
- Full base URL not stored by default
- Credential presence-only outside probe
- Cross-host redirects rejected (`follow_redirects=False` + policy evidence)
- Offline network tripwire available via `ALMS_PROBE_BLOCK_NETWORK`

## Native gate preservation

| Item | Value |
| --- | --- |
| G2 | blocked_credential |
| G3 | blocked_credential |
| G7 | not_started |
| L-01 | F2 / proposed |
| Phase 0 complete | false |
| Phase 1 Entry | not approved |
| Draft ModelRuntime | forbidden |

## D-006

Authorized and implemented as a separate compatibility track.
Not native evidence.

## Live

Status: `BLOCKED_CONFIGURATION`

Missing: `ALMS_COMPAT_CONFIRM_LIVE`, credentials, base URLs, models, endpoint IDs, allowed hosts.
No fake live report or evidence package was created.

## Stop condition

C0 complete for all eligible offline slices; live honestly blocked by missing fresh configuration.
