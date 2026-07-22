# Custom Endpoint Adapter Guide

## Purpose

Reusable guidance for future ALMS endpoint adapters based on Compatibility Lab C0 evidence.

Custom endpoint compatibility evidence is not native-provider evidence.
It does not satisfy G2 or G3.

## Declare API family

Choose exactly one:

- `openai_compatible` — Chat Completions through the OpenAI SDK with custom `base_url`
- `anthropic_compatible` — Messages through the Anthropic SDK with custom `base_url`

Do not invent a commercial lane ID from the API shape.

## Configure endpoint alias

Set a safe `endpoint_id` alias (for example `compat-openai-lab`).
Persist `endpoint_id`, `api_family`, and `boundary_kind` in evidence.
Do not persist the full base URL by default.

## Configure credentials safely

- Environment-only keys (`ALMS_COMPAT_*_API_KEY`)
- Outside the probe, record only `credential_present: true|false`
- Never store length, prefix, suffix, hash, or entropy
- Never commit values
- Never paste credentials into chat

## Preserve raw semantics

- Exercise the real SDK request construction path
- Capture wire-shaped or SDK-parsed endpoint-boundary artifacts
- Do not return pre-normalized objects from the transport seam
- Anthropic content blocks must stay Anthropic-shaped
- OpenAI Chat Completions must not be rewritten into Responses API shape inside the probe

## Normalize without provider claims

- Use evidence class `custom_endpoint_compatibility`
- Use ownership label `endpoint_boundary` for endpoint-owned usage and returned model
- Never label custom-endpoint fields `provider_native` without independent unmediated proof
- Provider and gateway claims remain claims

## Represent capabilities

Use distinct states:

```text
declared
observed_offline
observed_live
unsupported
inconclusive
not_tested
```

Do not infer capability from model names or marketing labels.

## Represent unsupported behavior

If the installed SDK lacks a safe custom `base_url` path:

```text
status: UNSUPPORTED
reason: installed SDK surface does not provide a safe supported configuration path
```

Do not fake support through an unrelated client family.

## Test retries

- Set SDK `max_retries=0`
- Measure outbound attempt count from the transport seam
- Do not infer zero attempts from configuration alone

## Test redirects

- Disable automatic redirect following where possible
- Reject cross-host redirects
- Reject HTTP downgrade
- Record redirect policy outcomes in boundary evidence

## Test streaming

- Preserve stream event shapes after SDK parsing
- Record terminal/finish state when present

## Test model identity

- Keep requested and returned model separate
- Missing returned model stays unavailable/null
- Mismatch is non-failing evidence

## Avoid native-gate contamination

- Do not write custom lanes into Phase 0 native gate calculations
- Do not close G2 or G3 with custom-endpoint evidence
- Use `execution_mode: live_custom_endpoint` for authorized live runs, never `live_native`
