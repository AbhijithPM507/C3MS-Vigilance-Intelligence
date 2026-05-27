from langgraph.graph import StateGraph
from backend.logic.state_schema import ComplaintState
from backend.logic.nodes.categorizer_node import categorize_node
from backend.logic.nodes.retrieval_node import retrieval_node
from backend.logic.nodes.validation_node import validation_node
from backend.logic.nodes.risk_analysis_node import risk_analysis_node
from backend.logic.nodes.escalation_node import escalation_node


def _route_after_validate(state):
    if state["validation_decision"] == "Context Good":
        return "analyze"
    if state.get("retrieval_attempts", 0) >= 3:
        return "analyze"
    return "retrieve"


def build_graph():

    workflow = StateGraph(ComplaintState)

    workflow.add_node("categorize", categorize_node)
    workflow.add_node("retrieve", retrieval_node)
    workflow.add_node("validate", validation_node)
    workflow.add_node("analyze", risk_analysis_node)
    workflow.add_node("escalate", escalation_node)

    workflow.set_entry_point("categorize")

    workflow.add_edge("categorize", "retrieve")
    workflow.add_edge("retrieve", "validate")

    workflow.add_conditional_edges(
        "validate",
        _route_after_validate,
        {
            "analyze": "analyze",
            "retrieve": "retrieve",
        },
    )

    workflow.add_conditional_edges(
        "analyze",
        lambda state: "escalate" if state["escalation_required"] else "__end__"
    )

    workflow.add_edge("escalate", "__end__")

    return workflow.compile()