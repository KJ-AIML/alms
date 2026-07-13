"""Audit provenance vocabulary (centrally owned).

PROVISIONAL — AUDIT INFRASTRUCTURE ONLY. NOT the ALMS runtime contract.

The ALMS Bible (Section 52) requires usage and evidence to "explicitly represent unknown
values and provenance rather than silently converting missing data to zero", and (the central
control plane rule) that the vocabulary be owned centrally "rather than letting each language
implementation invent one". This module is that single owned source of truth for P0.6C: it
names the provenance categories the audit system must be able to distinguish so that a
normalized field is never silently assumed to be provider-reported.

Not every category applies to every artifact. The mapping to existing evidence mechanisms is:

  * ``PROVIDER_NATIVE``       a provider's own reported value (e.g. OpenAI/Anthropic/Gemini
                              usage block; a provider_extension transcript event).
  * ``FRAMEWORK_NATIVE``      a framework's normalized value (e.g. LangChain ``usage_metadata``;
                              a framework_extension transcript event). NOT provider-reported.
  * ``SDK_CONVENIENCE``       an SDK convenience projection (e.g. ``output_text``) rather than
                              the authoritative raw object. Normalizers read authoritative raw
                              structures (items/content-blocks/steps), not convenience fields.
  * ``PROBE_DERIVED``         measured by the probe at the runtime boundary (raw run manifest
                              fields: exit code, retry_count_observed, timeout/cancel action).
  * ``NORMALIZER_DERIVED``    interpreted by a harness normalizer into the candidate audit
                              vocabulary; always carries a ``raw_ref`` back to raw evidence.
  * ``LOCAL_ESTIMATE``        computed locally by the harness (e.g. ``cost_estimated`` from a
                              pricing snapshot). Estimated is not measured.
  * ``FIXTURE_EXPECTED``      a value asserted by the offline fixture / mock, not observed from
                              a provider. Corresponds to ``execution_mode == "offline_mock"``.
  * ``UNAVAILABLE``           the value was not reported and is not knowable here (missing usage
                              stays null; never coerced to zero).
  * ``UNVERIFIED_UNTIL_LIVE`` a claim that only a real provider call can confirm (e.g. live
                              transport/retry behavior). Offline evidence cannot settle it.

The subset that legitimately labels a *usage token* summary is USAGE_SOURCES; the rest describe
other evidence kinds and are documented here so the distinctions exist in one owned place.
"""

from __future__ import annotations

PROVIDER_NATIVE = "provider_native"
FRAMEWORK_NATIVE = "framework_native"
SDK_CONVENIENCE = "sdk_convenience"
PROBE_DERIVED = "probe_derived"
NORMALIZER_DERIVED = "normalizer_derived"
LOCAL_ESTIMATE = "local_estimate"
FIXTURE_EXPECTED = "fixture_expected"
UNAVAILABLE = "unavailable"
UNVERIFIED_UNTIL_LIVE = "unverified_until_live"

# The full vocabulary, in the canonical order the neutrality matrix schema expects.
VOCABULARY: tuple[str, ...] = (
    PROVIDER_NATIVE,
    FRAMEWORK_NATIVE,
    SDK_CONVENIENCE,
    PROBE_DERIVED,
    NORMALIZER_DERIVED,
    LOCAL_ESTIMATE,
    FIXTURE_EXPECTED,
    UNAVAILABLE,
    UNVERIFIED_UNTIL_LIVE,
)

# Sources that may label a usage-token summary (result.usage.source enum, minus the audit-only
# "mixed"). A framework-normalized usage block is FRAMEWORK_NATIVE, never PROVIDER_NATIVE.
USAGE_SOURCES: frozenset[str] = frozenset(
    {PROVIDER_NATIVE, FRAMEWORK_NATIVE, LOCAL_ESTIMATE, UNAVAILABLE}
)

# Sources that may label an OBSERVED RETURNED MODEL identity (P0.6D, finding N-05).
# A model id read from a native provider response is PROVIDER_NATIVE (live); a model id exposed
# only through framework response metadata is FRAMEWORK_NATIVE (never provider-native merely
# because the string resembles a provider model id); a model taken from an SDK convenience
# projection rather than the authoritative resource is SDK_CONVENIENCE; an offline synthetic
# (mock/fixture) value is FIXTURE_EXPECTED and must never be labelled provider/framework-native;
# an unreported/absent value is UNAVAILABLE; a claim only a real call can settle is
# UNVERIFIED_UNTIL_LIVE. The requested model is request-side configuration, not an observation,
# so it never carries one of these.
MODEL_IDENTITY_SOURCES: frozenset[str] = frozenset(
    {
        PROVIDER_NATIVE,
        FRAMEWORK_NATIVE,
        SDK_CONVENIENCE,
        FIXTURE_EXPECTED,
        UNAVAILABLE,
        UNVERIFIED_UNTIL_LIVE,
    }
)


def is_known(term: str) -> bool:
    """True if ``term`` is a recognized provenance category (fail closed on typos)."""
    return term in VOCABULARY
