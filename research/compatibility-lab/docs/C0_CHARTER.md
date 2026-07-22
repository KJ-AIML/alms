# Compatibility Lab C0 Charter

## Track identity

| Field | Value |
| --- | --- |
| Track | Compatibility Lab C0 |
| Purpose | Audit and support model endpoints that expose OpenAI-compatible, Anthropic-compatible, gateway-routed, proxy-routed, or custom `base_url` APIs |
| Evidence class | `custom_endpoint_compatibility` |
| Branch | `research/custom-endpoint-compatibility-c0` |
| Source baseline | `research/runtime-audit-phase0` at `eda7589` |
| Deferred item | D-006 authorized as a separate compatibility track |

## Relationship to Phase 0

This workstream is **not** a continuation of the mandatory-offline Phase 0 campaign.
It does **not** replace native-provider live evidence.
It does **not** begin Phase 1A or production ModelRuntime.

Preserved Phase 0 facts (unchanged by C0):

- Phase 0 mandatory offline campaign: `ALL_ELIGIBLE_OFFLINE_WORK_COMPLETE`
- G2: `blocked_credential`
- G3: `blocked_credential`
- G7: `not_started`
- L-01: F2 / `proposed`
- Phase 0: not complete
- P0.8 Stress Semantics execution: not authorized
- Phase 1 Entry: not approved
- Draft ModelRuntime: forbidden

## Core evidence rule

Custom endpoints are valid engineering targets.
They are not invalid merely because they use a custom `base_url`.

Their evidence must remain truthful:

- Custom-endpoint evidence must never close G2, G3, or any native-provider live acceptance gate.
- Custom-endpoint behavior must never be labeled `provider_native` unless direct, unmediated provider-native evidence has independently proven that classification.
- A gateway may forward, transform, normalize, synthesize, remove, or relabel provider behavior. That uncertainty is preserved.

## Initial lane identities

| Lane ID | API family | SDK family | Boundary |
| --- | --- | --- | --- |
| `openai-compatible-custom` | `openai_compatible` | OpenAI Python SDK | custom endpoint / gateway / proxy / unknown |
| `anthropic-compatible-custom` | `anthropic_compatible` | Anthropic Python SDK | custom endpoint / gateway / proxy / unknown |

Do **not** create an `openrouter` lane unless repository evidence or configured endpoint metadata proves the service is specifically OpenRouter.
Do **not** infer commercial service identity from API shape or model ID.

## Non-goals

C0 does not:

- close G2 or G3
- replace native provider lanes
- begin ModelRuntime
- begin Phase 1
- implement LiteLLM Proxy
- implement Pydantic AI Gateway
- deploy production services
- publish a package

## Authority order

1. Safety and credential constraints in the C0 activation prompt
2. ALMS Bible locked decisions
3. Existing Development Specifications
4. Current Git and repository truth
5. Existing audit schemas and evidence contracts
6. Published P0.6 through P0.7E findings and reports
7. Compatibility Lab C0 DevSpec created by this campaign
8. Previous chat summaries
