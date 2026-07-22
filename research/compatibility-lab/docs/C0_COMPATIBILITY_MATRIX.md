# C0 Compatibility Matrix

## Scope

This matrix compares only Compatibility Lab lanes:

- `openai-compatible-custom`
- `anthropic-compatible-custom`

Canonical Phase 0 native/framework lanes are referenced for context only and are not
merged into this matrix.

Custom endpoint compatibility evidence is not native-provider evidence.
It does not satisfy G2 or G3.

## Machine-readable source

- Report: `reports/compatibility-matrix.json`
- Schema: `spec/compatibility-matrix.schema.json`

## Summary

| Dimension | openai-compatible-custom | anthropic-compatible-custom |
| --- | --- | --- |
| API family | openai_compatible | anthropic_compatible |
| SDK family | openai | anthropic |
| Request shape | chat.completions.create | messages.create |
| Role mapping | system/user messages | top-level system + content blocks |
| Structured output | response_format.json_schema | output_config.format.json_schema |
| Tools | function tool_calls | tool_use content blocks |
| Stream model | chat.completion.chunk SSE | Anthropic message event lifecycle |
| Usage shape | prompt/completion/total | input/output + cache fields |
| Model identity | requested/returned separate | requested/returned separate |
| Retry ownership | SDK max_retries=0, measured attempts | SDK max_retries=0, measured attempts |
| Redirect behavior | cross-host rejected | cross-host rejected |
| Provider verification | unverified | unverified |
| Evidence mode | offline_sdk_transport | offline_sdk_transport |

## Native gate preservation

| Gate / state | Value |
| --- | --- |
| G2 | blocked_credential |
| G3 | blocked_credential |
| G7 | not_started |
| Phase 0 complete | false |
| Phase 1 Entry | not approved |
