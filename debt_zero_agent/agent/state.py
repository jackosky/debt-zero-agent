"""Agent state for LangGraph workflow."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from debt_zero_agent.models import FixResult, FailedFix, SonarQubeIssue


class AgentState(TypedDict):
    """State maintained throughout the agent workflow."""
    
    # Input configuration
    repo_path: str
    issues: list[SonarQubeIssue]
    dry_run: bool
    llm_provider: str
    
    # Current processing state
    current_issue_index: int
    current_issue: SonarQubeIssue | None
    
    # Conversation history
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Results tracking
    successful_fixes: list[FixResult]
    failed_fixes: list[FailedFix]
    
    # Retry tracking
    retry_count: int
    max_retries: int
