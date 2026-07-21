"""Offline fixture corpus lint (DevSpec Tier 0 / Sections 21, 44, 79; P0.3 acceptance).

Validates every JSON under ``<root>/fixtures/`` against the fixture schema, checks for
duplicate IDs, requires non-empty ``expected_invariants``, and ensures every invariant
key is either a DevSpec Section 44 deterministic evaluator, an explicit
``PENDING_EVALUATORS`` entry, or an explicit ``MANUAL_REVIEW`` marker.

Also scans for provider-specific SDK method syntax in common fixtures, validates
capability vocabulary, and checks ``cost_class=offline`` vs ``live_required`` consistency.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .fixtures import Fixture, duplicate_ids, load_fixtures
from .schemas import validation_errors

# DevSpec Section 44 example invariant evaluators (deterministic, unit-tested).
DEVSPEC_EVALUATORS: frozenset[str] = frozenset(
    {
        "schema_valid",
        "expected_fields_equal",
        "non_empty_assistant_content",
        "expected_tool_name",
        "expected_tool_arguments",
        "tool_call_count",
        "terminal_state_present",
        "stream_has_monotonic_sequence",
        "usage_not_fabricated",
        "error_category_present",
    }
)

# Evaluator names declared in fixtures but not yet implemented in harness/invariants/.
# evaluate_invariants returns mode=manual_review / detail=pending evaluator for these.
PENDING_EVALUATORS: frozenset[str] = frozenset(
    {
        "argument_fragments_associated",
        "backoff_behavior_recorded",
        "caller_termination_observed",
        "candidate_category_recorded",
        "content_part_mapping_recorded",
        "continuation_after_tool_result",
        "distinct_call_ids_recorded",
        "embedding_dimensions_present",
        "final_status_present",
        "hidden_retry_detectable",
        "incremental_text",
        "native_error_preserved",
        "nested_values_preserved",
        "observed_structured_mode_recorded",
        "outbound_attempts_observed",
        "parallel_support_recorded",
        "partial_final_semantics_marked",
        "provider_work_evidence_recorded",
        "result_semantics_recorded",
        "retry_count_observed",
        "retry_interaction_recorded",
        "schema_transformations_recorded",
        "stable_call_linkage",
        "stream_started",
        "system_instruction_represented",
        "timeout_category_present",
        "timeout_owner_recorded",
        "tool_call_identity_preserved",
        "tool_choice_respected",
        "usage_finality_marked",
        "usage_metadata_recorded",
        "usage_presence_recorded",
        "usage_provenance_recorded",
        "usage_timing_recorded",
        "validation_location_recorded",
        "vector_output_shape_recorded",
    }
)

# Invariant keys that require explicit human review rather than automation.
MANUAL_REVIEW: frozenset[str] = frozenset()

# Committed capability vocabulary (aligned with fixture.schema.json feature enum).
CAPABILITY_VOCABULARY: frozenset[str] = frozenset(
    {
        "generation",
        "roles",
        "structured_output",
        "tools",
        "streaming",
        "cancellation",
        "timeout",
        "retry",
        "errors",
        "usage",
        "embeddings",
        "multimodal",
    }
)

# Provider/SDK method syntax that must not appear in common (non-extension) fixture text.
_PROVIDER_SYNTAX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bopenai\.responses\.create\b"),
    re.compile(r"\bopenai\.chat\.completions\.create\b"),
    re.compile(r"\banthropic\.messages\.create\b"),
    re.compile(r"\bChatOpenAI\b"),
    re.compile(r"\blitellm\.completion\b"),
    re.compile(r"\bgoogle\.genai\b"),
    re.compile(r"\bgenai\.Client\b"),
    re.compile(r"\bpydantic_ai\.Agent\b"),
)


@dataclass(frozen=True)
class LintIssue:
    fixture_id: str
    path: Path
    message: str


@dataclass
class LintReport:
    issues: list[LintIssue]

    @property
    def ok(self) -> bool:
        return not self.issues


def corpus_invariant_keys(fixtures: list[Fixture]) -> frozenset[str]:
    """Collect every ``expected_invariants`` key across ``fixtures``."""
    keys: set[str] = set()
    for fx in fixtures:
        inv = fx.data.get("expected_invariants")
        if isinstance(inv, dict):
            keys.update(inv)
    return frozenset(keys)


def allowed_invariant_keys(
    fixtures: list[Fixture] | None = None,
    *,
    reference_root: Path | None = None,
    extra_pending: frozenset[str] = PENDING_EVALUATORS,
    extra_manual: frozenset[str] = MANUAL_REVIEW,
) -> frozenset[str]:
    """Return evaluator names permitted in ``expected_invariants``.

    P0.3 acceptance requires every key to be a deterministic evaluator or an *explicit*
    pending/manual marker. Corpus keys are not auto-allowed merely by appearing on disk.
    """
    del fixtures, reference_root  # retained for call-site compatibility; unused by design
    return DEVSPEC_EVALUATORS | extra_pending | extra_manual


def _scan_provider_syntax(fx: Fixture) -> list[str]:
    """Return messages for provider-specific SDK syntax outside the extension object."""
    data = {k: v for k, v in fx.data.items() if k != "extension"}
    blob = json.dumps(data, ensure_ascii=False, sort_keys=True)
    hits: list[str] = []
    for pattern in _PROVIDER_SYNTAX_PATTERNS:
        match = pattern.search(blob)
        if match:
            hits.append(f"provider-specific method syntax: {match.group(0)}")
    return hits


def _check_capabilities(fx: Fixture) -> list[str]:
    caps = (fx.data.get("requirements") or {}).get("capabilities") or []
    bad = [c for c in caps if c not in CAPABILITY_VOCABULARY]
    if not bad:
        return []
    return [f"unknown capability name(s): {', '.join(sorted(bad))}"]


def _check_live_mock_consistency(fx: Fixture) -> list[str]:
    cost = fx.data.get("cost_class")
    req = fx.data.get("requirements") or {}
    live = req.get("live_required")
    if cost == "offline" and live is not False:
        return ["cost_class offline requires live_required false"]
    if live is False and cost not in ("offline", None) and req.get("supports_mock_mode") is False:
        return ["live_required false with supports_mock_mode false is inconsistent"]
    return []


def lint_fixtures(root: Path | None = None, *, reference_root: Path | None = None) -> LintReport:
    """Run all Tier-0 fixture lint checks against ``root`` (default: package corpus)."""
    del reference_root  # allowed keys no longer depend on a reference corpus union
    issues: list[LintIssue] = []
    fixtures = load_fixtures(root)
    allowed = allowed_invariant_keys()

    for fx in sorted(fixtures, key=lambda f: f.id):
        fid = fx.id
        try:
            schema_errors = validation_errors("fixture", fx.data, root)
            if schema_errors:
                issues.append(LintIssue(fid, fx.path, f"schema: {'; '.join(schema_errors)}"))
                continue

            inv = fx.data.get("expected_invariants")
            if not isinstance(inv, dict) or not inv:
                issues.append(
                    LintIssue(fid, fx.path, "expected_invariants: must be a non-empty object")
                )
                continue

            unknown = sorted(k for k in inv if k not in allowed)
            if unknown:
                issues.append(
                    LintIssue(
                        fid,
                        fx.path,
                        "unknown invariant evaluator(s): "
                        f"{', '.join(unknown)} "
                        "(add to PENDING_EVALUATORS or MANUAL_REVIEW in fixture_lint.py)",
                    )
                )

            for message in (
                _scan_provider_syntax(fx)
                + _check_capabilities(fx)
                + _check_live_mock_consistency(fx)
            ):
                issues.append(LintIssue(fid, fx.path, message))
        except Exception as exc:  # noqa: BLE001 - surface any load/parse failure
            issues.append(LintIssue(fid, fx.path, str(exc)))

    for dup in sorted(duplicate_ids(fixtures)):
        first = next(f for f in fixtures if f.id == dup)
        issues.append(LintIssue(dup, first.path, f"duplicate fixture id: {dup}"))

    issues.sort(key=lambda i: (i.fixture_id, i.message))
    return LintReport(issues=issues)


def format_report(report: LintReport) -> str:
    if report.ok:
        return "PASS fixture lint"
    lines = ["FAIL fixture lint"]
    for issue in report.issues:
        lines.append(f"FAIL fixture {issue.fixture_id} ({issue.path.name}): {issue.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Module entrypoint: ``python -m alms_audit.fixture_lint``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="research/runtime-audit directory (defaults to the one this package ships in)",
    )
    args = parser.parse_args(argv)
    root: Path | None = args.root
    report = lint_fixtures(root)
    print(format_report(report))
    if report.ok:
        count = len(load_fixtures(root))
        print(f"ok   {count} fixture(s)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
