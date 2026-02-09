"""Command-line interface for debt-zero-agent."""

import argparse
import json
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
        required=True,
        help="Path to SonarQube issues JSON file",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposed fixes without applying them",
    )
    
    parser.add_argument(
        "--llm",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per issue (default: 3)",
    )
    
    args = parser.parse_args()
    
    # Validate repo path
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load issues
    try:
        issues = load_issues(args.issues)
        print(f"Loaded {len(issues)} issues from {args.issues}")
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

