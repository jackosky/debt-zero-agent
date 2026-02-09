"""LangGraph workflow definition."""

from langgraph.graph import StateGraph, END

from debt_zero_agent.agent.nodes import (
    analyze_issue,
    apply_fix,
    finalize,
    select_next_issue,
    validate_fix,
)
from debt_zero_agent.agent.state import AgentState


def should_continue(state: AgentState) -> str:
    """Determine next step after selecting issue.
    
    Returns:
        Next node name or END
    """
    if state["current_issue"] is None:
        return "finalize"
    return "analyze"


def should_retry(state: AgentState) -> str:
    """Determine if fix should be retried after validation.
    
    Returns:
        Next node name
    """
    if state["retry_count"] >= state["max_retries"]:
        # Max retries reached, move to next issue
        return "select_next"
    
    # Check if validation passed (issue index was incremented)
    if state.get("_validation_passed", False):
        return "select_next"
    
    # Retry the fix
    return "apply"


def build_graph() -> StateGraph:
    """Build the LangGraph workflow.
    
    Returns:
        Compiled graph ready for execution
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("select_next", select_next_issue)
    workflow.add_node("analyze", analyze_issue)
    workflow.add_node("apply", apply_fix)
    workflow.add_node("validate", validate_fix)
    workflow.add_node("finalize", finalize)
    
    # Set entry point
    workflow.set_entry_point("select_next")
    
    # Add edges
    workflow.add_conditional_edges(
        "select_next",
        should_continue,
        {
            "analyze": "analyze",
            "finalize": "finalize",
        }
    )
    
    workflow.add_edge("analyze", "apply")
    workflow.add_edge("apply", "validate")
    
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "apply": "apply",
            "select_next": "select_next",
        }
    )
    
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
