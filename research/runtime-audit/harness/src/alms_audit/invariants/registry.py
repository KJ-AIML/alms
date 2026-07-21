"""Registry mapping invariant evaluator names to pure callables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import evaluators

EvaluatorFn = Callable[[dict, dict, dict | None, Any], tuple[bool | None, str, str]]

EVALUATORS: dict[str, EvaluatorFn] = {
    "usage_not_fabricated": evaluators.evaluate_usage_not_fabricated,
    "terminal_state_present": evaluators.evaluate_terminal_state_present,
    "non_empty_assistant_content": evaluators.evaluate_non_empty_assistant_content,
    "expected_tool_name": evaluators.evaluate_expected_tool_name,
    "expected_tool_arguments": evaluators.evaluate_expected_tool_arguments,
    "tool_call_count": evaluators.evaluate_tool_call_count,
    "schema_valid": evaluators.evaluate_schema_valid,
    "expected_fields_equal": evaluators.evaluate_expected_fields_equal,
    "stream_has_monotonic_sequence": evaluators.evaluate_stream_has_monotonic_sequence,
    "error_category_present": evaluators.evaluate_error_category_present,
}
