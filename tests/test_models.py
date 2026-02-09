"""Unit tests for SonarQube issue models."""

import pytest
from debt_zero_agent.models import (
    IssueSearchResponse,
    SonarQubeIssue,
    TextRange,
)


def test_text_range_creation():
    """Test TextRange model creation."""
    text_range = TextRange(startLine=10, endLine=15, startOffset=0, endOffset=50)
    assert text_range.startLine == 10
    assert text_range.endLine == 15
    assert text_range.startOffset == 0
    assert text_range.endOffset == 50


def test_sonarqube_issue_creation():
    """Test SonarQubeIssue model creation."""
    issue = SonarQubeIssue(
        key="AX1234",
        rule="python:S1234",
        severity="MAJOR",
        component="my-project:src/main.py",
        message="Remove this unused variable",
        line=42,
        type="CODE_SMELL",
        tags=["unused"],
    )
    assert issue.key == "AX1234"
    assert issue.rule == "python:S1234"
    assert issue.severity == "MAJOR"
    assert issue.type == "CODE_SMELL"
    assert issue.line == 42


def test_get_file_path():
    """Test file path extraction from component."""
    issue = SonarQubeIssue(
        key="AX1234",
        rule="python:S1234",
        severity="MAJOR",
        component="my-project:src/utils/helper.py",
        message="Test",
        type="BUG",
    )
    assert issue.get_file_path() == "src/utils/helper.py"


def test_get_file_path_no_colon():
    """Test file path extraction when no project key present."""
    issue = SonarQubeIssue(
        key="AX1234",
        rule="python:S1234",
        severity="MAJOR",
        component="src/main.py",
        message="Test",
        type="BUG",
    )
    assert issue.get_file_path() == "src/main.py"


def test_issue_search_response():
    """Test IssueSearchResponse model."""
    response = IssueSearchResponse(
        issues=[
            SonarQubeIssue(
                key="AX1",
                rule="python:S1",
                severity="MAJOR",
                component="proj:file.py",
                message="Bug",
                type="BUG",
            ),
            SonarQubeIssue(
                key="AX2",
                rule="python:S2",
                severity="MINOR",
                component="proj:file.py",
                message="Smell",
                type="CODE_SMELL",
            ),
        ],
        total=2,
        p=1,
        ps=100,
    )
    assert len(response.issues) == 2
    assert response.total == 2


def test_filter_by_type():
    """Test filtering issues by type."""
    response = IssueSearchResponse(
        issues=[
            SonarQubeIssue(
                key="AX1",
                rule="python:S1",
                severity="MAJOR",
                component="proj:file.py",
                message="Bug",
                type="BUG",
            ),
            SonarQubeIssue(
                key="AX2",
                rule="python:S2",
                severity="MINOR",
                component="proj:file.py",
                message="Smell",
                type="CODE_SMELL",
            ),
            SonarQubeIssue(
                key="AX3",
                rule="python:S3",
                severity="CRITICAL",
                component="proj:file.py",
                message="Vuln",
                type="VULNERABILITY",
            ),
        ],
        total=3,
    )
    
    bugs = response.filter_by_type("BUG")
    assert len(bugs) == 1
    assert bugs[0].type == "BUG"
    
    bugs_and_vulns = response.filter_by_type("BUG", "VULNERABILITY")
    assert len(bugs_and_vulns) == 2


def test_issue_from_json():
    """Test parsing issue from JSON dict."""
    json_data = {
        "key": "AX1234",
        "rule": "python:S1234",
        "severity": "MAJOR",
        "component": "my-project:src/main.py",
        "message": "Remove this unused variable",
        "line": 42,
        "textRange": {
            "startLine": 42,
            "endLine": 42,
            "startOffset": 4,
            "endOffset": 20,
        },
        "type": "CODE_SMELL",
        "tags": ["unused", "convention"],
    }
    
    issue = SonarQubeIssue(**json_data)
    assert issue.key == "AX1234"
    assert issue.textRange is not None
    assert issue.textRange.startLine == 42
    assert len(issue.tags) == 2
