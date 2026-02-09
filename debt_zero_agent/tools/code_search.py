"""Code search tool using ripgrep for fast searching."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool


@dataclass
class SearchResult:
    """Result from code search."""

    file_path: str
    line_number: int
    line_content: str
    context_before: list[str]
    context_after: list[str]


@tool
def search_code(repo_path: str, query: str, file_patterns: list[str] | None = None) -> list[dict]:
    """Search for code patterns in the repository using ripgrep.
    
    Uses ripgrep (rg) for fast searching, falls back to grep if not available.
    
    Args:
        repo_path: Absolute path to the repository root
        query: Search query (supports regex)
        file_patterns: Optional list of glob patterns (e.g., ['*.py', '*.js'])
        
    Returns:
        List of search results with file path, line number, and context
    """
    repo = Path(repo_path)
    
    # Try ripgrep first (much faster)
    try:
        cmd = ["rg", "--json", "--context", "2", "--max-count", "50"]
        
        # Add file type filters if specified
        if file_patterns:
            for pattern in file_patterns:
                cmd.extend(["--glob", pattern])
        
        cmd.append(query)
        cmd.append(str(repo))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode in [0, 1]:  # 0 = found, 1 = not found
            return _parse_ripgrep_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Ripgrep not available or timed out, fall back to grep
        pass
    
    # Fallback to grep
    return _grep_fallback(repo, query, file_patterns)


def _parse_ripgrep_output(output: str) -> list[dict]:
    """Parse ripgrep JSON output."""
    results = []
    current_match = {}
    context_before = []
    context_after = []
    
    for line in output.strip().split("\n"):
        if not line:
            continue
        
        try:
            data = json.loads(line)
            msg_type = data.get("type")
            
            if msg_type == "match":
                match_data = data["data"]
                results.append({
                    "file_path": match_data["path"]["text"],
                    "line_number": match_data["line_number"],
                    "line_content": match_data["lines"]["text"].rstrip(),
                    "context_before": context_before.copy(),
                    "context_after": [],  # Will be filled by subsequent context
                })
                context_before = []
            elif msg_type == "context":
                context_data = data["data"]
                context_line = context_data["lines"]["text"].rstrip()
                
                # Add to previous match's context_after if we have matches
                if results and len(results[-1]["context_after"]) < 2:
                    results[-1]["context_after"].append(context_line)
                else:
                    # Otherwise, it's context before the next match
                    if len(context_before) < 2:
                        context_before.append(context_line)
        except (json.JSONDecodeError, KeyError):
            continue
    
    return results[:50]


def _grep_fallback(repo: Path, query: str, file_patterns: list[str] | None) -> list[dict]:
    """Fallback to grep if ripgrep is not available."""
    results = []
    
    try:
        cmd = ["grep", "-rn", "-E", query, str(repo)]
        
        # Add file patterns
        if file_patterns:
            for pattern in file_patterns:
                cmd.extend(["--include", pattern])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        for line in result.stdout.strip().split("\n")[:50]:
            if not line:
                continue
            
            parts = line.split(":", 2)
            if len(parts) >= 3:
                file_path = parts[0]
                try:
                    line_number = int(parts[1])
                    line_content = parts[2]
                    
                    results.append({
                        "file_path": str(Path(file_path).relative_to(repo)),
                        "line_number": line_number,
                        "line_content": line_content,
                        "context_before": [],
                        "context_after": [],
                    })
                except (ValueError, OSError):
                    continue
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return results

