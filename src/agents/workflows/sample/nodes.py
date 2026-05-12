from src.agents.workflows.sample.state import SampleWorkflowState


async def normalize_query(state: SampleWorkflowState) -> SampleWorkflowState:
    query = (state.get("query") or "").strip()
    return {"query": query}


async def build_response(state: SampleWorkflowState) -> SampleWorkflowState:
    return {"response": f"Received: {state.get('query', '')}"}
