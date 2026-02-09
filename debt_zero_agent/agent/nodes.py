"""LangGraph nodes for the agent workflow."""

from langchain_core.messages import HumanMessage, SystemMessage

from debt_zero_agent.agent.llm import get_llm
from debt_zero_agent.agent.state import AgentState
from debt_zero_agent.models import FailedFix, FixResult, FixStatus
from debt_zero_agent.prompts.templates import ANALYZE_ISSUE_PROMPT
from debt_zero_agent.tools import generate_diff, read_file, write_file
from debt_zero_agent.validation import (
    detect_language_from_extension,
    locate_issue,
    validate_syntax,
)


def select_next_issue(state: AgentState) -> AgentState:
    """Select the next issue to process.
    
    Returns:
        Updated state with current issue set
    """
    if state["current_issue_index"] >= len(state["issues"]):
        # No more issues
        state["current_issue"] = None
        return state
    
    issue = state["issues"][state["current_issue_index"]]
    state["current_issue"] = issue
    state["retry_count"] = 0
    
    return state


def analyze_issue(state: AgentState) -> AgentState:
    """Analyze the current issue and plan a fix.
    
    Returns:
        Updated state with analysis in messages
    """
    issue = state["current_issue"]
    if not issue:
        return state
    
    # Get file content and AST context
    file_path = issue.get_file_path()
    content = read_file.invoke({
        "repo_path": state["repo_path"],
        "file_path": file_path,
    })
    
    # Locate issue in AST
    language = detect_language_from_extension(file_path)
    if language and issue.line:
        context = locate_issue(content, language, issue.line)
    else:
        # Fallback if language detection fails
        context = None
    
    # Create analysis prompt
    llm = get_llm(state["llm_provider"])
    
    prompt_values = {
        "issue_key": issue.key,
        "rule": issue.rule,
        "severity": issue.severity,
        "type": issue.type,
        "file_path": file_path,
        "line": issue.line or "N/A",
        "message": issue.message,
        "node_type": context.node_type if context else "N/A",
        "node_text": context.node_text[:100] if context else "N/A",
        "parent_type": context.parent_type if context else "N/A",
    }
    
    messages = ANALYZE_ISSUE_PROMPT.format_messages(**prompt_values)
    response = llm.invoke(messages)
    
    state["messages"].append(HumanMessage(content=str(messages[-1].content)))
    state["messages"].append(response)
    
    return state


def apply_fix(state: AgentState) -> AgentState:
    """Generate and apply the fix.
    
    Returns:
        Updated state with fix applied
    """
    issue = state["current_issue"]
    if not issue:
        return state
    
    file_path = issue.get_file_path()
    
    # Read current content
    original_content = read_file.invoke({
        "repo_path": state["repo_path"],
        "file_path": file_path,
    })
    
    # For now, use a simple prompt to get the fix
    # In a real implementation, this would be more sophisticated
    llm = get_llm(state["llm_provider"])
    
    fix_prompt = f"""Based on the previous analysis, generate the complete fixed file content.

Original file: {file_path}
Issue: {issue.message}

Return ONLY the fixed code, no explanations."""
    
    response = llm.invoke([
        SystemMessage(content="You are a code fixing assistant."),
        HumanMessage(content=fix_prompt),
    ])
    
    fixed_content = response.content
    
    # Store in state for validation
    state["messages"].append(HumanMessage(content=fix_prompt))
    state["messages"].append(response)
    
    # Temporarily store for validation
    state["_temp_fixed_content"] = fixed_content
    state["_temp_original_content"] = original_content
    
    return state


def validate_fix(state: AgentState) -> AgentState:
    """Validate the proposed fix.
    
    Returns:
        Updated state with validation results
    """
    issue = state["current_issue"]
    if not issue:
        return state
    
    file_path = issue.get_file_path()
    original_content = state.get("_temp_original_content", "")
    fixed_content = state.get("_temp_fixed_content", "")
    
    # Validate syntax
    language = detect_language_from_extension(file_path)
    if language:
        validation = validate_syntax(fixed_content, language)
        
        if not validation.valid:
            # Validation failed
            state["retry_count"] += 1
            
            if state["retry_count"] >= state["max_retries"]:
                # Max retries reached, mark as failed
                failed_fix = FailedFix(
                    issue_key=issue.key,
                    file_path=file_path,
                    status=FixStatus.VALIDATION_ERROR,
                    error_message="; ".join(validation.errors),
                    llm_provider=state["llm_provider"],
                    iterations=state["retry_count"],
                )
                state["failed_fixes"].append(failed_fix)
                state["current_issue_index"] += 1
            
            return state
    
    # Validation passed, apply the fix
    diff = generate_diff.invoke({
        "original": original_content,
        "modified": fixed_content,
        "file_path": file_path,
    })
    
    # Write the fix
    write_result = write_file.invoke({
        "repo_path": state["repo_path"],
        "file_path": file_path,
        "content": fixed_content,
        "dry_run": state["dry_run"],
    })
    
    # Record successful fix
    fix_result = FixResult(
        issue_key=issue.key,
        file_path=file_path,
        original_content=original_content,
        fixed_content=fixed_content,
        diff=diff,
        status=FixStatus.SUCCESS,
        llm_provider=state["llm_provider"],
        iterations=state["retry_count"] + 1,
    )
    state["successful_fixes"].append(fix_result)
    state["current_issue_index"] += 1
    
    return state


def finalize(state: AgentState) -> AgentState:
    """Finalize the workflow and generate report.
    
    Returns:
        Final state with summary
    """
    total_issues = len(state["issues"])
    successful = len(state["successful_fixes"])
    failed = len(state["failed_fixes"])
    
    summary = f"""
Fix Summary:
- Total issues: {total_issues}
- Successfully fixed: {successful}
- Failed: {failed}
- Success rate: {successful/total_issues*100:.1f}%
"""
    
    state["messages"].append(SystemMessage(content=summary))
    
    return state
