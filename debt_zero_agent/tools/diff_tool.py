"""Diff generation tool using native Unix diff command."""

import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool


@tool
def generate_diff(original: str, modified: str, file_path: str = "file") -> str:
    """Generate unified diff using native Unix diff command.
    
    Args:
        original: Original file content
        modified: Modified file content
        file_path: File path for diff header
        
    Returns:
        Unified diff as string
    """
    # Write content to temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f1:
        f1.write(original)
        temp1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f2:
        f2.write(modified)
        temp2 = f2.name
    
    try:
        # Run diff command
        result = subprocess.run(
            ['diff', '-u', '--label', f'a/{file_path}', '--label', f'b/{file_path}', temp1, temp2],
            capture_output=True,
            text=True,
        )
        
        # diff returns 0 if no changes, 1 if changes found, 2 on error
        if result.returncode in [0, 1]:
            return result.stdout
        else:
            # Fallback to Python difflib if diff command fails
            return _difflib_fallback(original, modified, file_path)
    finally:
        # Clean up temp files
        Path(temp1).unlink(missing_ok=True)
        Path(temp2).unlink(missing_ok=True)


def _difflib_fallback(original: str, modified: str, file_path: str) -> str:
    """Fallback to Python difflib if native diff fails."""
    import difflib
    
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    
    return "".join(diff)


def generate_diff_stats(original: str, modified: str) -> dict:
    """Generate statistics about the diff.
    
    Args:
        original: Original content
        modified: Modified content
        
    Returns:
        Dictionary with diff statistics
    """
    # Use native diff with --brief for quick stats
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f1:
        f1.write(original)
        temp1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f2:
        f2.write(modified)
        temp2 = f2.name
    
    try:
        result = subprocess.run(
            ['diff', '-u', temp1, temp2],
            capture_output=True,
            text=True,
        )
        
        # Parse diff output for stats
        additions = 0
        deletions = 0
        
        for line in result.stdout.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        
        original_lines = len(original.splitlines())
        modified_lines = len(modified.splitlines())
        
        return {
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions,
            "original_lines": original_lines,
            "modified_lines": modified_lines,
        }
    finally:
        Path(temp1).unlink(missing_ok=True)
        Path(temp2).unlink(missing_ok=True)

