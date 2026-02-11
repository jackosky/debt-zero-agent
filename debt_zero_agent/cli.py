"""Command-line interface for debt-zero-agent."""

import argparse
import json
import os
import sys
from pathlib import Path

from debt_zero_agent.agent import AgentState, build_graph
from debt_zero_agent.models import IssueSearchResponse


def load_issues(issues_path: str) -> list:
    """Load SonarQube issues from JSON file.
    
    Args:
        issues_path: Path to issues JSON file
        
    Returns:
        List of SonarQubeIssue objects
    """
    with open(issues_path) as f:
        data = json.load(f)
    
    response = IssueSearchResponse(**data)
    return response.issues


def fetch_issues_from_api(
    project_key: str,
    sonar_url: str = "https://sonarcloud.io",
    token: str | None = None,
    limit: int = 10,
) -> list:
    """Fetch issues directly from SonarQube API.
    
    Args:
        project_key: SonarQube project key
        sonar_url: SonarQube server URL
        token: Authentication token (optional, reads from SONAR_TOKEN env var)
        limit: Maximum number of issues to fetch (default: 10)
        
    Returns:
        List of SonarQubeIssue objects
    """
    import requests
    
    token = token or os.getenv("SONAR_TOKEN")
    if not token:
        print("Warning: SONAR_TOKEN not set, API may be rate-limited", file=sys.stderr)
    
    url = f"{sonar_url.rstrip('/')}/api/issues/search"
    filtered_issues = []
    page = 1
    page_size = 100  # Fetch more per page to account for filtering
    
    # Keep fetching until we have enough non-external issues
    while len(filtered_issues) < limit:
        params = {
            "componentKeys": project_key,
            "types": "CODE_SMELL,BUG,VULNERABILITY",
            "resolved": "false",
            "ps": page_size,
            "p": page,
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                auth=(token, "") if token else None,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            
            response_obj = IssueSearchResponse(**data)
            
            # Filter out external rules (external_roslyn, external_*, etc.)
            page_filtered = [
                issue for issue in response_obj.issues
                if not issue.rule.startswith("external_")
            ]
            
            filtered_issues.extend(page_filtered)
            
            # Check if we've reached the end
            total_issues = data.get("total", 0)
            if page * page_size >= total_issues or not response_obj.issues:
                break
            
            page += 1
            
        except Exception as e:
            print(f"Error fetching issues from API: {e}", file=sys.stderr)
            sys.exit(1)
    
    issues = filtered_issues[:limit]  # Enforce limit
    print(f"Fetched {len(issues)} issues from {sonar_url} (excluded external rules)")
    return issues


def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Automatically fix SonarQube issues using LLM-powered agent"
    )
    
    parser.add_argument(
        "repo_path",
        help="Path to the repository root",
    )
    
    parser.add_argument(
        "-i", "--issues",
        help="Path to SonarQube issues JSON file",
    )
    
    parser.add_argument(
        "--fetch-issues",
        metavar="PROJECT_KEY",
        help="Fetch issues from SonarQube API (requires SONAR_TOKEN env var)",
    )
    
    parser.add_argument(
        "--sonar-url",
        default="https://sonarcloud.io",
        help="SonarQube server URL (default: https://sonarcloud.io)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposed fixes without applying them",
    )
    
    parser.add_argument(
        "--llm",
        choices=["openai", "anthropic", "gemini"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per issue (default: 3)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of issues to process (default: 10)",
    )
    
    parser.add_argument(
        "--max-lines-changed",
        type=int,
        default=30,
        help="Maximum lines a single fix can change (default: 30)",
    )
    
    parser.add_argument(
        "--max-change-ratio",
        type=float,
        default=0.1,
        help="Maximum file change ratio (default: 0.1 = 10%%)",
    )
    
    args = parser.parse_args()
    
    # Validate that either --issues or --fetch-issues is provided
    if not args.issues and not args.fetch_issues:
        parser.error("Either --issues or --fetch-issues must be specified")
    
    if args.issues and args.fetch_issues:
        parser.error("Cannot specify both --issues and --fetch-issues")
    
    # Validate repo path
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load issues
    try:
        if args.fetch_issues:
            issues = fetch_issues_from_api(
                project_key=args.fetch_issues,
                sonar_url=args.sonar_url,
                limit=args.limit,
            )
        else:
            issues = load_issues(args.issues)
            print(f"Loaded {len(issues)} issues from {args.issues}")
            # Apply limit to loaded issues too
            if len(issues) > args.limit:
                print(f"Limiting to first {args.limit} issues")
                issues = issues[:args.limit]
    except Exception as e:
        print(f"Error loading issues: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not issues:
        print("No issues to fix!")
        return
    
    # Initialize agent state
    initial_state: AgentState = {
        "repo_path": str(repo_path),
        "issues": issues,
        "dry_run": args.dry_run,
        "llm_provider": args.llm,
        "current_issue_index": 0,
        "current_issue": None,
        "messages": [],
        "successful_fixes": [],
        "failed_fixes": [],
        "retry_count": 0,
        "max_retries": args.max_retries,
        "max_lines_changed": args.max_lines_changed,
        "max_change_ratio": args.max_change_ratio,
    }
    
    # Build and run the workflow
    print(f"\nStarting agent workflow with {args.llm}...")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")
    
    graph = build_graph()
    
    try:
        final_state = graph.invoke(initial_state)
        
        # Print results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        
        print(f"\nSuccessful fixes: {len(final_state['successful_fixes'])}")
        for fix in final_state["successful_fixes"]:
            print(f"  ✓ {fix.issue_key}: {fix.file_path}")
        
        print(f"\nFailed fixes: {len(final_state['failed_fixes'])}")
        for fix in final_state["failed_fixes"]:
            print(f"  ✗ {fix.issue_key}: {fix.error_message}")
        
        success_rate = (
            len(final_state["successful_fixes"]) / len(issues) * 100
            if issues else 0
        )
        print(f"\nSuccess rate: {success_rate:.1f}%")
        
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError running workflow: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

