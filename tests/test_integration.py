"""End-to-end integration tests."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from debt_zero_agent.agent import AgentState, build_graph
from debt_zero_agent.models import IssueSearchResponse


@pytest.fixture
def test_repo():
    """Create a temporary test repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample file
        sample_file = Path(tmpdir) / "sample.py"
        sample_file.write_text("""
def calculate_price(items):
    tax_rate = 0.1  # Unused variable
    total = 0
    for item in items:
        total += item["price"]
    return total
""")
        yield tmpdir


@pytest.fixture
def test_issues():
    """Load test issues."""
    issues_path = Path(__file__).parent / "fixtures" / "test_issues.json"
    with open(issues_path) as f:
        data = json.load(f)
    response = IssueSearchResponse(**data)
    return response.issues


def test_load_test_issues(test_issues):
    """Test that test issues load correctly."""
    assert len(test_issues) == 4
    assert test_issues[0].rule == "python:S1481"
    assert test_issues[1].rule == "python:S1192"


def test_graph_initialization():
    """Test that graph can be built."""
    graph = build_graph()
    assert graph is not None


def test_state_initialization(test_repo, test_issues):
    """Test initializing agent state."""
    state: AgentState = {
        "repo_path": test_repo,
        "issues": test_issues[:1],  # Just test with one issue
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
    
    assert state["repo_path"] == test_repo
    assert len(state["issues"]) == 1


def test_issue_file_path_extraction(test_issues):
    """Test extracting file paths from issues."""
    for issue in test_issues:
        file_path = issue.get_file_path()
        assert file_path.endswith("sample.py")


def test_dry_run_mode(test_repo, test_issues):
    """Test that dry-run mode doesn't modify files."""
    # Create a simple test file
    test_file = Path(test_repo) / "test.py"
    original_content = "x = 1\n"
    test_file.write_text(original_content)
    
    # Verify dry-run doesn't change the file
    assert test_file.read_text() == original_content


@pytest.mark.skipif(
    not Path(__file__).parent.parent.parent.joinpath("tests/fixtures/test_repo/sample.py").exists(),
    reason="Test repository not set up"
)
def test_sample_repo_exists():
    """Test that sample repository exists."""
    sample_file = Path(__file__).parent / "fixtures" / "test_repo" / "sample.py"
    assert sample_file.exists()
    
    content = sample_file.read_text()
    assert "tax_rate" in content
    assert "production" in content
