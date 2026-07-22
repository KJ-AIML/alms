# Compatibility Lab C0 Autonomous Roadmap

## Source baseline

| Field | Value |
| --- | --- |
| Phase 0 branch | `research/runtime-audit-phase0` |
| Baseline commit | `eda7589` |
| C0 branch | `research/custom-endpoint-compatibility-c0` |
| Campaign state | `.heli-harness/state/compatibility-campaign.md` |

## Slice order

| Slice | Goal | Status |
| --- | --- | --- |
| C0.0 | Charter, DevSpec, roadmap, baseline | complete |
| C0.1 | Endpoint configuration and secret-safety contract | complete |
| C0.2 | `openai-compatible-custom` offline lane | complete |
| C0.3 | `anthropic-compatible-custom` offline lane | complete |
| C0.4 | Endpoint identity and provenance contract | complete |
| C0.5 | Capability fingerprinting | complete |
| C0.6 | Compatibility comparison matrix | complete |
| C0.7 | Optional limited live validation | blocked (`BLOCKED_CONFIGURATION`) |
| C0.8 | Adapter authoring and conformance kit | complete |
| C0.9 | Full workstream review and closeout | complete |

## Stop condition

All eligible offline slices complete; live compatibility honestly blocked by missing fresh configuration.

## Resume instructions

1. Read `.heli-harness/state/compatibility-campaign.md`
2. Verify branch `research/custom-endpoint-compatibility-c0` is clean and linear
3. Live C0.7 requires fresh local `ALMS_COMPAT_*` configuration only
4. Do not reopen Phase 0 mandatory-offline campaign
5. Do not close G2/G3 with custom-endpoint evidence
