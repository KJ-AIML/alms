"""Zero-retry policy: every retry owner is zero and a one-model-request limit is enforced.

Retries are MEASURED by FunctionModel invocation count, never inferred from configuration. Each
case builds an Agent with the probe's real config (client.AGENT_RETRIES + client.usage_limits) so
the tests bind to what the probe actually applies.
"""

from __future__ import annotations

import pytest
from pydantic_ai import Agent, Tool
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from probe import client


def _counter():
    calls = {"n": 0}
    return calls


def test_retry_budgets_are_all_zero():
    intro = client.isolation_introspection()
    budgets = intro["retry_budgets"]
    assert budgets["output_validation_retries"] == 0
    assert budgets["tool_retries"] == 0
    assert budgets["per_tool_retries"] == 0
    assert budgets["request_limit"] == 1


def test_malformed_structured_output_does_not_retry():
    from pydantic import BaseModel
    from pydantic_ai import NativeOutput
    from pydantic_ai.profiles import ModelProfile

    calls = _counter()

    class Person(BaseModel):
        name: str
        age: int

    def fn(messages, info):
        calls["n"] += 1
        return ModelResponse(
            parts=[TextPart(content='{"name": "Alice"}')],  # missing required 'age'
            usage=RequestUsage(input_tokens=1, output_tokens=1),
            model_name="syn",
            finish_reason="stop",
        )

    agent = Agent(
        FunctionModel(fn, model_name="syn", profile=ModelProfile(supports_json_schema_output=True)),
        output_type=NativeOutput(Person),
        retries=client.AGENT_RETRIES,
    )
    with pytest.raises(UnexpectedModelBehavior):
        agent.run_sync("x", usage_limits=client.usage_limits())
    assert calls["n"] == 1  # no second FunctionModel invocation


def test_json_parse_failure_does_not_retry():
    from pydantic_ai import NativeOutput, StructuredDict
    from pydantic_ai.profiles import ModelProfile

    calls = _counter()
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}

    def fn(messages, info):
        calls["n"] += 1
        return ModelResponse(
            parts=[TextPart(content="not json at all")],
            usage=RequestUsage(input_tokens=1, output_tokens=1),
            model_name="syn",
            finish_reason="stop",
        )

    agent = Agent(
        FunctionModel(fn, model_name="syn", profile=ModelProfile(supports_json_schema_output=True)),
        output_type=NativeOutput(StructuredDict(schema, name="s")),
        retries=client.AGENT_RETRIES,
    )
    with pytest.raises(UnexpectedModelBehavior):
        agent.run_sync("x", usage_limits=client.usage_limits())
    assert calls["n"] == 1


def test_tool_argument_validation_failure_does_not_retry():
    calls = _counter()

    def _tool(city: str) -> str:
        return f"weather in {city}"

    tool = Tool.from_schema(
        _tool,
        name="get_weather",
        description="weather",
        json_schema={
            "type": "object",
            "required": ["city"],
            "properties": {"city": {"type": "string"}},
        },
    )

    def fn(messages, info):
        calls["n"] += 1
        return ModelResponse(
            parts=[ToolCallPart(tool_name="get_weather", args={"wrong": 1}, tool_call_id="c1")],
            usage=RequestUsage(input_tokens=1, output_tokens=1),
            model_name="syn",
            finish_reason="tool_call",
        )

    agent = Agent(
        FunctionModel(fn, model_name="syn"),
        tools=[tool],
        retries=client.AGENT_RETRIES,
    )
    # The exception class varies (arg mismatch surfaces as a runtime error); the invariant under
    # test is that the failure did NOT trigger a second model request (tool retries = 0).
    with pytest.raises(Exception):  # noqa: B017
        agent.run_sync("x", usage_limits=client.usage_limits())
    assert calls["n"] == 1  # invalid tool args did NOT trigger a retry model request


def test_one_request_limit_blocks_second_model_turn():
    calls = _counter()

    def _tool(city: str) -> str:
        return "sunny"

    tool = Tool.from_schema(
        _tool,
        name="get_weather",
        description="weather",
        json_schema={
            "type": "object",
            "required": ["city"],
            "properties": {"city": {"type": "string"}},
        },
    )

    def fn(messages, info):
        calls["n"] += 1
        return ModelResponse(
            parts=[
                ToolCallPart(tool_name="get_weather", args={"city": "Paris"}, tool_call_id="c1")
            ],
            usage=RequestUsage(input_tokens=1, output_tokens=1),
            model_name="syn",
            finish_reason="tool_call",
        )

    # A normal (executing) tool would force a SECOND model request to produce the final answer;
    # request_limit=1 blocks it with UsageLimitExceeded rather than allowing a silent extra call.
    agent = Agent(
        FunctionModel(fn, model_name="syn"),
        tools=[tool],
        retries=client.AGENT_RETRIES,
    )
    with pytest.raises(UsageLimitExceeded):
        agent.run_sync("x", usage_limits=client.usage_limits())
    assert calls["n"] == 1
