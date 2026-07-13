"""ALMS Phase 0 Anthropic native audit probe (Messages API).

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23) which is NOT the future ModelRuntime contract. The Anthropic SDK is used only
inside this isolated probe; the central harness never imports it. This lane deliberately
preserves Anthropic-native semantics (top-level system, content blocks, tool_use blocks,
stop_reason, native stream events) to challenge OpenAI-shaped assumptions (DevSpec
Section 50); it does not reshape them into OpenAI forms in raw evidence.
"""

__version__ = "0.0.0"
PROBE_ID = "anthropic-native"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
