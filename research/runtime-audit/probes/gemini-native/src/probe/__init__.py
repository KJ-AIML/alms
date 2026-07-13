"""ALMS Phase 0 Gemini native audit probe (Interactions API).

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23) which is NOT the future ModelRuntime contract. The google-genai SDK is used
only inside this isolated probe; the central harness never imports it. This lane uses the
Gemini Interactions API (`client.interactions.create`) and deliberately preserves
Interactions-native concepts (Interaction resource, chronological steps, response_format,
native stream events) to challenge OpenAI-shaped assumptions (DevSpec Section 51); it does
not reshape them into OpenAI forms in raw evidence.

Note: the Gemini Interactions API is Generally Available (since June 2026). In google-genai
2.11.0 it is exposed through `google.genai.interactions`; the public module re-exports generated
types/resources implemented under internal `_gaos` modules (an SDK implementation detail, not the
API lifecycle). Generated Python types and signatures may evolve on SDK upgrade, so offline
evidence is modelled with schema-validated native dictionaries using the SDK's real field names,
and `client.interactions.create` must be revalidated when google-genai is upgraded.
"""

__version__ = "0.0.0"
PROBE_ID = "gemini-native"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
