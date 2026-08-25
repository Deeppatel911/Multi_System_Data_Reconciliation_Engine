from graph.state import ReconciliationState


def route_after_resolution(state: ReconciliationState) -> str:
    """LangGraph conditional edge: decide whether the profile needs human sign-off
    before persisting, or can be saved immediately."""
    if state.get("human_approval_required") is True:
        return "approval_node"
    return "persist_node"
