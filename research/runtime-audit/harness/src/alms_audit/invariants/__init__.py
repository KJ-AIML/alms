"""Deterministic invariant evaluation over fixture + result + transcript."""

from __future__ import annotations

from typing import Any

from .registry import EVALUATORS

__all__ = ["evaluate_invariants", "EVALUATORS"]


def evaluate_invariants(
    fixture_data: dict,
    result_data: dict,
    transcript_data: dict | None = None,
) -> list[dict[str, Any]]:
    """Evaluate every key in ``fixture_data['expected_invariants']``.

    Returns one record per invariant::

        {"name": str, "passed": bool|None, "detail": str, "mode": "deterministic"|"manual_review"}
    """
    expected = fixture_data.get("expected_invariants")
    if not isinstance(expected, dict):
        return []

    results: list[dict[str, Any]] = []
    for name in sorted(expected):
        value = expected[name]
        evaluator = EVALUATORS.get(name)
        if evaluator is None:
            results.append(
                {
                    "name": name,
                    "passed": None,
                    "detail": "pending evaluator",
                    "mode": "manual_review",
                }
            )
            continue

        passed, detail, mode = evaluator(fixture_data, result_data, transcript_data, value)
        results.append(
            {
                "name": name,
                "passed": passed,
                "detail": detail,
                "mode": mode,
            }
        )
    return results
