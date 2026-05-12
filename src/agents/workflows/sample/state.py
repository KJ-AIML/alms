from typing import TypedDict


class SampleWorkflowState(TypedDict, total=False):
    query: str
    response: str
    errors: list[str]
