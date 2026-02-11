"""File writing tool for applying fixes."""

from pathlib import Path

from langchain_core.tools import tool


class EditError(Exception):
    """Raised when an edit cannot be applied."""
    pass


def apply_edit(original_content: str, old_code: str, new_code: str) -> str:
    """Apply a search-and-replace edit to content.
    
    Args:
        original_content: Original file content
        old_code: Exact string to find and replace
        new_code: Replacement string
        
    Returns:
        Modified content with the replacement applied
        
    Raises:
        EditError: If old_code is not found or appears multiple times
    """
    # Count occurrences
    count = original_content.count(old_code)
    
    if count == 0:
        raise EditError(
            f"Could not find the old_code in the file. "
            f"The code to replace must match exactly, including whitespace."
        )
    
    if count > 1:
        raise EditError(
            f"Found {count} occurrences of old_code. "
            f"The code to replace must be unique. "
            f"Include more context lines to make it unique."
        )
    
    # Apply the replacement
    return original_content.replace(old_code, new_code, 1)


@tool
def write_file(repo_path: str, file_path: str, content: str, dry_run: bool = False) -> dict:
    """Write modified content to a file.
    
    Args:
        repo_path: Absolute path to the repository root
        file_path: Relative path to the file
        content: New file content
        dry_run: If True, don't actually write the file
        
    Returns:
        Dictionary with status and message
    """
    full_path = Path(repo_path) / file_path
    
    if dry_run:
        return {
            "status": "dry_run",
            "message": f"Would write {len(content)} bytes to {file_path}",
            "file_path": file_path,
        }
    
    # Create parent directories if needed
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "status": "success",
            "message": f"Successfully wrote {len(content)} bytes to {file_path}",
            "file_path": file_path,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write file: {str(e)}",
            "file_path": file_path,
        }
