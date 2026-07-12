"""Injectable model boundary for the LangChain lane.

`build_chat_model` returns a real `langchain_openai.ChatOpenAI` bound to DIRECT OpenAI with
all automatic retries disabled (used only on the live path, which is NOT exercised offline).
`OfflineChatModel` is a NARROW deterministic fake `BaseChatModel`: it exercises the real
LangChain machinery around it (message conversion, `bind_tools`, `with_structured_output`,
streaming aggregation, usage propagation) without ever touching the network. It is not a
universal provider framework, and it does not replicate ChatOpenAI's provider-request
translation — that remains unverified_until_live.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import PrivateAttr


def build_chat_model(api_key: str, timeout_ms: int, model: str):
    """Construct a real ChatOpenAI against DIRECT OpenAI. Import is local so the module loads
    without a key. NO base_url is set: the lane must not be silently redirected to OpenRouter
    or any gateway. max_retries=0 disables LangChain's wrapper retries AND the underlying
    openai client's retries (verified: both report 0), so the audit sees true single-attempt
    behavior; hidden retries would corrupt attempt evidence and could add unplanned cost.
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        max_retries=0,
        timeout=max(timeout_ms, 1) / 1000.0,
    )


def retry_introspection(model: Any) -> dict:
    """Record each retry owner independently (DevSpec Sections 64 and 80).

    Never claims zero merely because a fixture requested zero: it reads the effective
    configuration off the constructed objects, and records calls actually observed.
    """
    chat_max = getattr(model, "max_retries", None)
    root_client = getattr(model, "root_client", None)
    client_max = getattr(root_client, "max_retries", None) if root_client is not None else None
    calls = getattr(model, "calls_observed", None)
    return {
        "langchain_runnable_retry": "none (no .with_retry applied)",
        "chat_model_max_retries": chat_max,
        "openai_client_max_retries": client_max,
        "http_transport_retry": "owned by openai client (max_retries above)",
        "calls_observed": calls,
        "retries_observed": (calls - 1) if isinstance(calls, int) else None,
    }


class FakeFrameworkError(Exception):
    """Mimics a framework-wrapped provider error with an underlying cause chain."""


def _usage() -> dict:
    return {"input_tokens": 9, "output_tokens": 5, "total_tokens": 14}


def _canned_args(scenario: str) -> dict:
    if scenario == "structured":
        return {"name": "Alice", "age": 30}
    return {"city": "Paris"}  # tools scenario


class OfflineChatModel(BaseChatModel):
    """Deterministic offline fake. `scenario` selects the canned content shape; the framework
    path (invoke / bind_tools / with_structured_output / stream) is chosen by execute() from
    the operation, exactly as it would be for a real model."""

    scenario: str = "generation"
    model_label: str = "offline-fake"
    _calls: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "alms-langchain-offline-fake"

    @property
    def calls_observed(self) -> int:
        return self._calls

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001 - matches BaseChatModel signature
        formatted = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=formatted, **kwargs)

    def _tool_name(self, kwargs: dict) -> str | None:
        tools = kwargs.get("tools") or []
        if tools:
            return tools[0].get("function", {}).get("name")
        return None

    def _ai_message(self, kwargs: dict) -> AIMessage:
        name = self._tool_name(kwargs)
        if self.scenario in ("structured", "tools") and name:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": name,
                        "args": _canned_args(self.scenario),
                        "id": f"call_{self.scenario}_1",
                        "type": "tool_call",
                    }
                ],
                usage_metadata=_usage(),
                response_metadata={"finish_reason": "tool_calls", "model_name": self.model_label},
            )
        return AIMessage(
            content="Hello there, friend.",
            usage_metadata=_usage(),
            response_metadata={"finish_reason": "stop", "model_name": self.model_label},
        )

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:  # noqa: ANN001
        self._calls += 1
        return ChatResult(generations=[ChatGeneration(message=self._ai_message(kwargs))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):  # noqa: ANN001
        self._calls += 1
        deltas = ["one\n", "two\n", "three\n"]
        for i, tok in enumerate(deltas):
            last = i == len(deltas) - 1
            meta = {"finish_reason": "stop", "model_name": self.model_label} if last else {}
            chunk = AIMessageChunk(
                content=tok,
                response_metadata=meta,
                usage_metadata=_usage() if last else None,
            )
            if run_manager is not None:
                run_manager.on_llm_new_token(tok, chunk=ChatGenerationChunk(message=chunk))
            yield ChatGenerationChunk(message=chunk)
