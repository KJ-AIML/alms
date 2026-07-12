"""ALMS Phase 0 OpenAI native audit probe (Responses API).

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23) which is NOT the future ModelRuntime contract. The OpenAI SDK is used only
inside this isolated probe; the central harness never imports it.
"""

__version__ = "0.0.0"
PROBE_ID = "openai-native"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
