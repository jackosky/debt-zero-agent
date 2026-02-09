"""File reading tool for LangChain agent."""

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(repo_path: str, file_path: str) -> str:
    """Read file content from the repository.
    
    Args:
        repo_path: Absolute path to the repository root
        file_path: Relative path to the file within the repository
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    full_path = Path(repo_path) / file_path
    
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not full_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding for non-UTF8 files
        with open(full_path, "r", encoding="latin-1") as f:
            return f.read()


@tool
def read_file_lines(repo_path: str, file_path: str, start_line: int, end_line: int) -> str:
    """Read specific lines from a file.
    
    Args:
        repo_path: Absolute path to the repository root
        file_path: Relative path to the file
        start_line: Starting line number (1-indexed, inclusive)
        end_line: Ending line number (1-indexed, inclusive)
        
    Returns:
        Content of specified lines
    """
    content = read_file.invoke({"repo_path": repo_path, "file_path": file_path})
    lines = content.splitlines()
    
    # Convert to 0-indexed
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    
    return "\n".join(lines[start_idx:end_idx])
