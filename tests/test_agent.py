"""Unit tests for agent core components."""

import os
from unittest.mock import Mock, patch

import pytest
from debt_zero_agent.agent import AgentState, build_graph, get_llm
from debt_zero_agent.models import SonarQubeIssue


# LLM Factory Tests


def test_get_llm_openai():
    """Test getting OpenAI LLM."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        llm = get_llm("openai")
        assert llm is not None
        assert llm.model_name == "gpt-4o"


def test_get_llm_anthropic():
    """Test getting Anthropic LLM."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        llm = get_llm("anthropic")
        assert llm is not None
        assert llm.model == "claude-3-5-sonnet-20241022"


def test_get_llm_missing_key():
    """Test error when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="API_KEY"):
            get_llm("openai")


def test_get_llm_invalid_provider():
    """Test error with invalid provider."""
    with pytest.raises(ValueError, match="Invalid provider"):
        get_llm("invalid")


# State Tests


def test_agent_state_creation():
    """Test creating AgentState."""
    state: AgentState = {
        "repo_path": "/tmp/repo",
        "issues": [],
        "dry_run": True,
        "llm_provider": "openai",
        "current_issue_index": 0,
        "current_issue": None,
        "messages": [],
        "successful_fixes": [],
        "failed_fixes": [],
        "retry_count": 0,
        "max_retries": 3,
    }
    
    assert state["repo_path"] == "/tmp/repo"
    assert state["dry_run"] is True
    assert state["max_retries"] == 3


# Graph Tests


def test_build_graph():
    """Test building the LangGraph workflow."""
    graph = build_graph()
    assert graph is not None
    
    # Graph should have nodes
    assert hasattr(graph, "nodes")


def test_graph_has_entry_point():
    """Test that graph has proper entry point."""
    graph = build_graph()
    # The compiled graph should be callable
    assert callable(graph.invoke)


# Integration Test (without actual LLM calls)


def test_workflow_initialization():
    """Test initializing workflow state."""
    issue = SonarQubeIssue(
        key="TEST-1",
        rule="python:S1234",
        severity="MAJOR",
        component="project:test.py",
        message="Test issue",
        type="CODE_SMELL",
    )
    
    initial_state: AgentState = {
        "repo_path": "/tmp/test",
        "issues": [issue],
        "dry_run": True,
        "llm_provider": "openai",
        "current_issue_index": 0,
        "current_issue": None,
        "messages": [],
        "successful_fixes": [],
        "failed_fixes": [],
        "retry_count": 0,
        "max_retries": 3,
    }
    
    assert len(initial_state["issues"]) == 1
    assert initial_state["current_issue"] is None
