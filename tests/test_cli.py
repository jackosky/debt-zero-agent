"""Unit tests for CLI."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from debt_zero_agent.cli import load_issues, main


def test_load_issues():
    """Test loading issues from JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "total": 1,
            "issues": [{
                "key": "TEST-1",
                "rule": "python:S1234",
                "severity": "MAJOR",
                "component": "project:test.py",
                "message": "Test issue",
                "type": "CODE_SMELL",
            }]
        }, f)
        temp_file = f.name
    
    try:
        issues = load_issues(temp_file)
        assert len(issues) == 1
        assert issues[0].key == "TEST-1"
    finally:
        Path(temp_file).unlink()


def test_cli_help():
    """Test CLI help message."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['debt-zero-agent', '--help']):
            main()
    
    assert exc_info.value.code == 0


def test_cli_missing_required_args():
    """Test CLI with missing required arguments."""
    with pytest.raises(SystemExit):
        with patch('sys.argv', ['debt-zero-agent']):
            main()


def test_cli_invalid_repo_path():
    """Test CLI with invalid repository path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"total": 0, "issues": []}, f)
        temp_file = f.name
    
    try:
        with pytest.raises(SystemExit) as exc_info:
            with patch('sys.argv', [
                'debt-zero-agent',
                '/nonexistent/path',
                '--issues', temp_file,
            ]):
                main()
        
        assert exc_info.value.code == 1
    finally:
        Path(temp_file).unlink()


def test_cli_no_issues():
    """Test CLI with empty issues file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"total": 0, "issues": []}, f)
        temp_file = f.name
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with patch('sys.argv', [
                'debt-zero-agent',
                tmpdir,
                '--issues', temp_file,
            ]):
                main()  # Should exit gracefully
        finally:
            Path(temp_file).unlink()
