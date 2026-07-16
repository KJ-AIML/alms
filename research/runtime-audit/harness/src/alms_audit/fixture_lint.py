"""Offline fixture corpus lint (DevSpec Tier 0 / Sections 21, 44, 79).

Validates every JSON under ``<root>/fixtures/`` against the fixture schema, checks for
duplicate IDs, requires non-empty ``expected_invariants``, and ensures every invariant
key is a known evaluator name (DevSpec Section 44 examples plus the committed corpus
union) or is listed in ``PENDING_EVALUATORS`` / ``MANUAL_REVIEW``.
"""

from __future__ import annotations

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
PENDING_EVALUATORS: frozenset[str] = frozenset()

# Invariant keys that require explicit human review rather than automation.
MANUAL_REVIEW: frozenset[str] = frozenset()


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

    Keys come from DevSpec Section 44 examples, every key used in the reference
    fixture corpus (defaults to the package's committed ``fixtures/`` tree), plus
    explicit ``PENDING_EVALUATORS`` and ``MANUAL_REVIEW`` entries.
    """
    if fixtures is None:
        from .schemas import default_root

        fixtures = load_fixtures(reference_root or default_root())
    return DEVSPEC_EVALUATORS | corpus_invariant_keys(fixtures) | extra_pending | extra_manual


def lint_fixtures(root: Path | None = None, *, reference_root: Path | None = None) -> LintReport:
    """Run all Tier-0 fixture lint checks against ``root`` (default: package corpus)."""
    from .schemas import default_root

    issues: list[LintIssue] = []
    fixtures = load_fixtures(root)
    ref = reference_root if reference_root is not None else (root or default_root())
    allowed = allowed_invariant_keys(reference_root=ref)

    for fx in fixtures:
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
        except Exception as exc:  # noqa: BLE001 - surface any load/parse failure
            issues.append(LintIssue(fid, fx.path, str(exc)))

    for dup in duplicate_ids(fixtures):
        first = next(f for f in fixtures if f.id == dup)
        issues.append(LintIssue(dup, first.path, f"duplicate fixture id: {dup}"))

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
