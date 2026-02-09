"""File writing tool for applying fixes."""

from pathlib import Path

from langchain_core.tools import tool


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
