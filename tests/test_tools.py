"""Unit tests for tools."""

import tempfile
from pathlib import Path

import pytest
from debt_zero_agent.tools import (
    generate_diff,
    generate_diff_stats,
    read_file,
    read_file_lines,
    search_code,
    write_file,
)


# File Reader Tests


def test_read_file():
    """Test reading a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("print('hello')\n")
        
        content = read_file.invoke({"repo_path": tmpdir, "file_path": "test.py"})
        assert content == "print('hello')\n"


def test_read_file_not_found():
    """Test reading non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError):
            read_file.invoke({"repo_path": tmpdir, "file_path": "missing.py"})


def test_read_file_lines():
    """Test reading specific lines from a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\n")
        
        content = read_file_lines.invoke({
            "repo_path": tmpdir,
            "file_path": "test.py",
            "start_line": 2,
            "end_line": 3,
        })
        assert content == "line2\nline3"


# Code Search Tests


def test_search_code():
    """Test searching for code patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "file1.py").write_text("def foo():\n    pass\n")
        (Path(tmpdir) / "file2.py").write_text("def bar():\n    foo()\n")
        
        results = search_code.invoke({
            "repo_path": tmpdir,
            "query": "foo",
            "file_patterns": ["*.py"],
        })
        
        assert len(results) >= 2  # Should find in both files


def test_search_code_regex():
    """Test regex search."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "test.py").write_text("x = 10\ny = 20\nz = 30\n")
        
        results = search_code.invoke({
            "repo_path": tmpdir,
            "query": r"[xyz] = \d+",
            "file_patterns": ["*.py"],
        })
        
        assert len(results) == 3


# File Writer Tests


def test_write_file():
    """Test writing a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_file.invoke({
            "repo_path": tmpdir,
            "file_path": "new.py",
            "content": "print('test')\n",
            "dry_run": False,
        })
        
        assert result["status"] == "success"
        assert Path(tmpdir, "new.py").read_text() == "print('test')\n"


def test_write_file_dry_run():
    """Test dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_file.invoke({
            "repo_path": tmpdir,
            "file_path": "new.py",
            "content": "print('test')\n",
            "dry_run": True,
        })
        
        assert result["status"] == "dry_run"
        assert not Path(tmpdir, "new.py").exists()


def test_write_file_creates_directories():
    """Test that parent directories are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = write_file.invoke({
            "repo_path": tmpdir,
            "file_path": "subdir/nested/file.py",
            "content": "test",
            "dry_run": False,
        })
        
        assert result["status"] == "success"
        assert Path(tmpdir, "subdir/nested/file.py").exists()


# Diff Tool Tests


def test_generate_diff():
    """Test generating unified diff."""
    original = "line1\nline2\nline3\n"
    modified = "line1\nmodified\nline3\n"
    
    diff = generate_diff.invoke({
        "original": original,
        "modified": modified,
        "file_path": "test.py",
    })
    
    assert "@@" in diff  # Unified diff format
    assert "-line2" in diff
    assert "+modified" in diff


def test_generate_diff_stats():
    """Test diff statistics."""
    original = "line1\nline2\nline3\n"
    modified = "line1\nmodified\nline3\nline4\n"
    
    stats = generate_diff_stats(original, modified)
    
    assert stats["additions"] == 2  # modified + line4
    assert stats["deletions"] == 1  # line2
    assert stats["total_changes"] == 3
    assert stats["original_lines"] == 3
    assert stats["modified_lines"] == 4


def test_generate_diff_no_changes():
    """Test diff with no changes."""
    content = "line1\nline2\n"
    
    diff = generate_diff.invoke({
        "original": content,
        "modified": content,
        "file_path": "test.py",
    })
    
    assert diff == ""  # No diff when content is identical
