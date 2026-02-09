"""Additional CLI tests for issue fetching."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from debt_zero_agent.cli import fetch_issues_from_api


@patch('requests.get')
def test_fetch_issues_from_api_success(mock_get):
    """Test fetching issues from API successfully."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "total": 2,
        "issues": [
            {
                "key": "TEST-1",
                "rule": "python:S1481",
                "severity": "MAJOR",
                "component": "project:test.py",
                "message": "Test issue 1",
                "type": "CODE_SMELL",
            },
            {
                "key": "TEST-2",
                "rule": "python:S1192",
                "severity": "MINOR",
                "component": "project:test.py",
                "message": "Test issue 2",
                "type": "CODE_SMELL",
            },
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    issues = fetch_issues_from_api("test-project", token="test-token")
    
    assert len(issues) == 2
    assert issues[0].key == "TEST-1"
    assert issues[1].key == "TEST-2"


@patch('requests.get')
def test_fetch_issues_with_limit(mock_get):
    """Test that limit is enforced."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "total": 20,
        "issues": [
            {
                "key": f"TEST-{i}",
                "rule": "python:S1481",
                "severity": "MAJOR",
                "component": "project:test.py",
                "message": f"Test issue {i}",
                "type": "CODE_SMELL",
            }
            for i in range(20)
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    issues = fetch_issues_from_api("test-project", token="test-token", limit=5)
    
    assert len(issues) == 5


@patch('requests.get')
def test_fetch_issues_api_error(mock_get):
    """Test handling API errors."""
    mock_get.side_effect = Exception("API Error")
    
    with pytest.raises(SystemExit):
        fetch_issues_from_api("test-project", token="test-token")
