# License and Third-Party Note

This `research/runtime-audit/` lab is part of the `alms` repository and is covered by
the repository's top-level [`LICENSE`](../../LICENSE).

## Third-party runtimes

Phase 0 probes execute against third-party runtime SDKs and LLM provider APIs
(e.g. LangChain, OpenAI, Anthropic, Gemini, LiteLLM, PydanticAI). Those SDKs are
**not** vendored here. Each probe declares its own dependencies in its own isolated
project (`probes/<lane>/pyproject.toml`) and remains subject to the upstream project's
license and each provider's API terms of service.

## Evidence artifacts

Raw run artifacts under `runs/` are local, gitignored, and may contain provider
responses. They must be redacted before any artifact is promoted into `evidence/`
(DevSpec §85 Raw Artifact Redaction). No API keys or secrets belong in any committed file.
