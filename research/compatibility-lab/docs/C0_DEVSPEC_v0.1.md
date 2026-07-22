# Compatibility Lab C0 Development Specification v0.1

## Status

Normative for Compatibility Lab C0 only.
Does not amend Phase 0 Runtime Audit DevSpec gate meanings.
Does not authorize Phase 1 Entry or Draft ModelRuntime.

## 1. Workstream purpose

Audit and support model endpoints that expose OpenAI-compatible, Anthropic-compatible,
gateway-routed, proxy-routed, or custom `base_url` APIs.

Evidence class: `custom_endpoint_compatibility`.

## 2. Non-goals

C0 does not:

- close G2 or G3
- replace native provider lanes (`openai-native`, `anthropic-native`, `gemini-native`,
  `langchain`, `litellm-sdk`, `pydantic-ai-agent`)
- begin ModelRuntime or Phase 1
- implement LiteLLM Proxy or Pydantic AI Gateway
- deploy production services
- publish a package
- label custom-endpoint fields `provider_native` without independent unmediated proof

## 3. Lane identities

| Lane ID | API family | SDK family |
| --- | --- | --- |
| `openai-compatible-custom` | `openai_compatible` | `openai` Python SDK |
| `anthropic-compatible-custom` | `anthropic_compatible` | `anthropic` Python SDK |

Lane IDs are fixed for C0. Commercial gateway names are not lane IDs unless proven.

## 4. Endpoint families

| Family | Request surface (C0) |
| --- | --- |
| `openai_compatible` | Chat Completions (`client.chat.completions.create`) via OpenAI SDK with custom `base_url` |
| `anthropic_compatible` | Messages (`client.messages.create`) via Anthropic SDK with custom `base_url` |

OpenAI-compatible C0 intentionally uses Chat Completions rather than Responses API because
most custom/gateway endpoints expose `/v1/chat/completions`, not Responses.

## 5. Evidence classes

| Class | Meaning |
| --- | --- |
| `custom_endpoint_compatibility` | Observed at a custom, gateway, or proxy boundary |
| `provider_native` | Reserved for direct unmediated provider evidence (Phase 0 native lanes only) |

Custom lanes must not contribute to native gate calculations.

## 6. Credential policy

Environment-only credentials. Outside the child probe process, store only:

```text
credential_present: true | false
```

Never store credential length, prefix, suffix, hash, or entropy.
Never print, log, serialize, or commit credential values.
Do not use credentials that appeared in chat history.
Never ask a human to paste a credential into chat.

Candidate variables (values never committed):

```text
ALMS_COMPAT_OPENAI_BASE_URL
ALMS_COMPAT_OPENAI_API_KEY
ALMS_COMPAT_OPENAI_MODEL
ALMS_COMPAT_OPENAI_ENDPOINT_ID
ALMS_COMPAT_ANTHROPIC_BASE_URL
ALMS_COMPAT_ANTHROPIC_API_KEY
ALMS_COMPAT_ANTHROPIC_MODEL
ALMS_COMPAT_ANTHROPIC_ENDPOINT_ID
ALMS_COMPAT_CONFIRM_LIVE
ALMS_COMPAT_HARD_CALL_CAP
ALMS_COMPAT_MAX_OUTPUT_TOKENS
ALMS_COMPAT_ALLOWED_HOSTS
```

## 7. Base URL policy

Live mode requires:

- HTTPS scheme
- no embedded credentials
- no username/password URI authority
- no fragment
- no unexpected query parameters
- host allowlist match (`ALMS_COMPAT_ALLOWED_HOSTS`)
- redirect host changes rejected
- localhost permitted only for offline tests

Evidence stores `endpoint_id`, `api_family`, and `boundary_kind`.
Evidence must not store the complete base URL by default.

## 8. Model identity policy

Represent separately:

- `requested_model`
- `observed_returned_model`
- `observed_returned_model_source`
- `model_identity_match`
- `raw_model_reference`

Do not infer provider identity from model name.
Do not transform a model mismatch into failure.
Do not strip model prefixes or aliases.
Do not copy requested model into returned model when absent.

## 9. Gateway identity policy

`configured_provider_claim` and `configured_gateway_claim` are unverified claims.
Do not promote claims to verified identity from:

- model name
- URL hostname alone
- response object class
- OpenAI-compatible or Anthropic-compatible shape
- SDK selected

## 10. Capability vocabulary

Capability states used in C0 profiles:

| State | Meaning |
| --- | --- |
| `declared` | Stated by endpoint configuration or documentation only |
| `observed_offline` | Demonstrated through offline SDK + transport evidence |
| `observed_live` | Demonstrated through authorized live custom-endpoint calls |
| `unsupported` | Demonstrably not supported |
| `inconclusive` | Exercise ran but semantics could not be decided |
| `not_tested` | Not exercised |

Do not infer capability from model names or marketing labels.

Separate:

- request accepted by SDK
- request accepted by endpoint
- response structurally returned
- semantic behavior observed
- invariant satisfied

## 11. Usage and cost provenance

Usage fields from custom endpoints use endpoint-boundary provenance, never `provider_native`
unless independently proven.

Monetary cost may be unavailable. Never fabricate USD estimates from native-provider pricing.
Call cap and token cap are authoritative.

## 12. Structured-output policy

Record the request mode actually sent (for example OpenAI `response_format` /
`json_schema`, Anthropic `output_config.format`). Preserve raw response shape.
Do not force OpenAI chat-completion shape onto Anthropic evidence.

## 13. Tool policy

Preserve tool request and tool-call response shapes at the endpoint boundary.
OpenAI-compatible: function tools on Chat Completions.
Anthropic-compatible: `tool_use` content blocks.

## 14. Streaming policy

Preserve stream event shapes as returned by the SDK after wire parsing.
Record terminal state when present.

## 15. Error policy

Capture SDK exception class, status code when present, and message after redaction.
Missing fields stay missing.

## 16. Redirect policy

Cross-host redirects are rejected.
HTTP downgrade is rejected.
Redirect host changes are security failures, not soft warnings.

## 17. Live-call policy

Authorized only when all are true:

- `ALMS_COMPAT_CONFIRM_LIVE=1`
- credential present
- base URL present
- endpoint ID present
- model present
- allowed host present
- working tree clean
- offline suites green
- live plan generated
- budget and call cap accepted

Live execution mode: `live_custom_endpoint` (never `live_native`).

Maximum:

- 6 provider requests per configured lane
- 12 total requests
- 0 retries
- 256 output tokens per request
- 30 second timeout per request

Start with GEN-001 smoke only. Proceed to remaining base fixtures only after smoke success.

Forbidden live fixtures in C0: ERROR-001, RETRY-001, CANCEL-001, TIMEOUT-001,
parallel tools, multimodal, embeddings.

## 18. Budget policy

`ALMS_COMPAT_HARD_CALL_CAP` and `ALMS_COMPAT_MAX_OUTPUT_TOKENS` are authoritative.
Stop immediately on unexpected billing or quota behavior.

## 19. Gate separation

| Gate / state | C0 effect |
| --- | --- |
| G2 | unchanged (`blocked_credential`) |
| G3 | unchanged (`blocked_credential`) |
| G7 | unchanged (`not_started`) |
| L-01 | unchanged unless user explicitly accepts a finding decision |
| Phase 0 complete | unchanged (false) |
| Phase 1 Entry | unchanged (not approved) |

Every compatibility report must state:

> Custom endpoint compatibility evidence is not native-provider evidence.
> It does not satisfy G2 or G3.

## 20. Exit criteria

C0 offline exit requires:

- Charter, DevSpec, roadmap, baseline published on the C0 branch
- Configuration and secret-safety contract with tests
- OpenAI-compatible offline lane with real SDK request construction
- Anthropic-compatible offline lane or honest `UNSUPPORTED`
- Endpoint identity and provenance decision recorded
- Capability profiles for both lanes
- Compatibility matrix with schema validation
- Adapter guide and security checklist
- Final report and findings ledger
- D-006 updated factually (authorized and implemented as separate track)
- Native gates unchanged
- Offline: provider calls = 0, credentials required = 0

Live compatibility is optional: complete when authorized configuration is present,
otherwise honestly `BLOCKED_CONFIGURATION` without fake evidence.

## 21. Provenance decision (C0.4 outcome target)

Existing nine-term provenance vocabulary remains authoritative for central terms.
Custom-endpoint boundary values use additive endpoint-identity fields and, where needed,
`endpoint_boundary` as an evidence ownership label in compatibility artifacts only.
A new central provenance enum term is **not** added unless reproducible evidence proves
the nine-term set cannot represent ownership without corruption.
