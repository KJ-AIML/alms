from langgraph.graph import END, START, StateGraph

from src.agents.workflows.sample.nodes import build_response, normalize_query
from src.agents.workflows.sample.state import SampleWorkflowState


def build_sample_workflow():
    workflow = StateGraph(SampleWorkflowState)
    workflow.add_node("normalize_query", normalize_query)
    workflow.add_node("build_response", build_response)

    workflow.add_edge(START, "normalize_query")
    workflow.add_edge("normalize_query", "build_response")
    workflow.add_edge("build_response", END)

    return workflow.compile()
