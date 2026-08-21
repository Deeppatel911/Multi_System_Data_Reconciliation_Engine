from graph.state import ReconciliationState


def route_after_resolution(state: ReconciliationState) -> str:
    """LangGraph conditional edge: decide whether the profile needs human sign-off
    before persisting, or can be saved immediately."""
    if state.get("human_approval_required") is True:
        return "__end__"
    return "persist_node"
