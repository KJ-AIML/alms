# C0 Endpoint Identity and Provenance

## Purpose

Prevent provider, gateway, SDK, endpoint, and model identity from being conflated in
custom-endpoint evidence.

## Identity model

Each compatibility run records:

| Field | Meaning |
| --- | --- |
| `endpoint_id` | Safe user-defined alias |
| `endpoint_family` | `openai_compatible` or `anthropic_compatible` |
| `boundary_kind` | `custom_endpoint`, `gateway`, `proxy`, or `unknown` |
| `sdk_family` | Actual client SDK (`openai` or `anthropic`) |
| `configured_provider_claim` | Unverified claim from configuration |
| `configured_gateway_claim` | Unverified service identity claim |
| `requested_model` | Model string sent in the request |
| `observed_returned_model` | Model string present in the endpoint response, or null |
| `observed_returned_model_source` | Ownership of the returned model observation |
| `model_identity_match` | Boolean compare, or null when returned model is absent |
| `raw_model_reference` | Unmodified returned model string |
| `execution_mode` | `offline_sdk_transport` or `live_custom_endpoint` |

## Forbidden inferences

Do not infer provider identity from:

- model name
- URL hostname alone
- response object class
- OpenAI-compatible or Anthropic-compatible shape
- SDK selected

Do not:

- transform a model mismatch into failure
- strip model prefixes or aliases
- copy requested model into returned model when absent

## Provenance vocabulary audit

Central Phase 0 vocabulary (nine terms in `alms_audit.provenance`):

```text
provider_native
framework_native
sdk_convenience
probe_derived
normalizer_derived
local_estimate
fixture_expected
unavailable
unverified_until_live
```

### Decision: B

**An additive endpoint-boundary field is sufficient.**

Outcome code: `B` (see `alms_compat.identity.PROVENANCE_DECISION`).

Rationale:

- Custom-endpoint usage and returned-model fields are owned by the endpoint/gateway boundary,
  not by a verified unmediated provider.
- Labeling those fields `provider_native` would be false provenance.
- Labeling them `framework_native` would incorrectly imply a framework normalization path.
- `fixture_expected` applies only to offline fixture expectations, not live custom responses.
- Therefore compatibility artifacts use the additive ownership label `endpoint_boundary` for
  endpoint-owned observations, without mutating the central nine-term enum.

A new central provenance enum term is **not** required for C0.

If a future finding shows that `endpoint_boundary` cannot be consumed by shared comparison
machinery without corruption, promote it through the full requirements:

- reproducible evidence
- definition
- ownership semantics
- backward compatibility
- schema migration
- tests
- comparison updates
- human-review note

## Evidence class

All C0 runs use:

```text
evidence_class: custom_endpoint_compatibility
```

Custom endpoint compatibility evidence is not native-provider evidence.
It does not satisfy G2 or G3.
