from langgraph.graph import StateGraph, END

from graph.state import ReconciliationState
from graph.nodes import fetch_all_data_node, persist_node
from graph.resolver import resolution_node
from graph.edges import route_after_resolution

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
graph_builder = StateGraph(ReconciliationState)

graph_builder.add_node("fetch", fetch_all_data_node)
graph_builder.add_node("resolve", resolution_node)
graph_builder.add_node("persist", persist_node)

graph_builder.set_entry_point("fetch")

graph_builder.add_edge("fetch", "resolve")

graph_builder.add_conditional_edges(
    "resolve",
    route_after_resolution,
    {
        "__end__": END,
        "persist_node": "persist",
    },
)

graph_builder.add_edge("persist", END)

app = graph_builder.compile()
