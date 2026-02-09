"""Tests for SonarQube client."""

from unittest.mock import Mock, patch

import pytest
from debt_zero_agent.sonarqube import RuleDescription, SonarQubeClient


@pytest.fixture
def mock_response():
    """Mock SonarQube API response."""
    return {
        "rule": {
            "key": "python:S1481",
            "name": "Unused local variables should be removed",
            "htmlDesc": "<p>Remove unused variables</p>",
            "type": "CODE_SMELL",
            "severity": "MINOR",
        }
    }


def test_sonarqube_client_init():
    """Test SonarQube client initialization."""
    client = SonarQubeClient()
    assert client.base_url == "https://sonarcloud.io"


def test_sonarqube_client_custom_url():
    """Test SonarQube client with custom URL."""
    client = SonarQubeClient(base_url="https://custom.sonarqube.com")
    assert client.base_url == "https://custom.sonarqube.com"


@patch('requests.Session.get')
def test_get_rule_success(mock_get, mock_response):
    """Test fetching rule successfully."""
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status = Mock()
    
    client = SonarQubeClient()
    rule = client.get_rule("python:S1481")
    
    assert rule is not None
    assert rule.key == "python:S1481"
    assert rule.name == "Unused local variables should be removed"
    assert "Remove unused variables" in rule.htmlDesc


@patch('requests.Session.get')
def test_get_rule_failure(mock_get):
    """Test handling API failure."""
    mock_get.side_effect = Exception("API Error")
    
    client = SonarQubeClient()
    rule = client.get_rule("python:S1481")
    
    assert rule is None


@patch('requests.Session.get')
def test_search_rules(mock_get):
    """Test searching for rules."""
    mock_get.return_value.json.return_value = {
        "rules": [
            {
                "key": "python:S1481",
                "name": "Unused variables",
                "htmlDesc": "<p>Description</p>",
                "type": "CODE_SMELL",
                "severity": "MINOR",
            }
        ]
    }
    mock_get.return_value.raise_for_status = Mock()
    
    client = SonarQubeClient()
    rules = client.search_rules(language="py")
    
    assert len(rules) == 1
    assert rules[0].key == "python:S1481"


def test_rule_description_model():
    """Test RuleDescription model."""
    rule = RuleDescription(
        key="python:S1481",
        name="Test rule",
        htmlDesc="<p>Description</p>",
        type="CODE_SMELL",
        severity="MINOR",
    )
    
    assert rule.key == "python:S1481"
    assert rule.type == "CODE_SMELL"
