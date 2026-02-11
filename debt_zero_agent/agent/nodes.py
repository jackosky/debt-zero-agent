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
    
    Fetches rule details from SonarQube API to enrich the prompt.
    
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
    
    # Fetch rule details from SonarQube API
    rule_description = ""
    try:
        from debt_zero_agent.sonarqube import SonarQubeClient
        
        sonar_url = state.get("sonar_url", "https://sonarcloud.io")
        client = SonarQubeClient(base_url=sonar_url)
        rule = client.get_rule(issue.rule)
        
        if rule:
            # Strip HTML tags for cleaner prompt
            import re
            clean_desc = re.sub(r'<[^>]+>', '', rule.htmlDesc)
            rule_description = f"\n**Rule Details**:\n{clean_desc[:500]}"
    except Exception as e:
        # Continue without rule details if API fails
        pass
    
    # Create analysis prompt
    llm = get_llm(state["llm_provider"])
    
    prompt_values = {
        "issue_key": issue.key,
        "rule": issue.rule,
        "severity": issue.severity,
        "type": issue.type,
        "file_path": file_path,
        "line": issue.line or "N/A",
        "message": issue.message + rule_description,
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
    import json
    
    issue = state["current_issue"]
    if not issue:
        return state
    
    file_path = issue.get_file_path()
    
    # Read current content
    original_content = read_file.invoke({
        "repo_path": state["repo_path"],
        "file_path": file_path,
    })
    
    # Use targeted fix prompt for JSON-based edits
    from debt_zero_agent.prompts.templates import TARGETED_FIX_PROMPT
    from debt_zero_agent.tools import EditError, apply_edit
    
    llm = get_llm(state["llm_provider"])
    
    # Build the prompt with accumulated context from previous messages
    prompt_values = {
        "message": issue.message,
        "file_path": file_path,
        "line": issue.line or "N/A",
        "file_content": original_content,
    }
    
    messages = TARGETED_FIX_PROMPT.format_messages(**prompt_values)
    
    # Use accumulated messages for context (includes analysis from previous step)
    full_messages = state["messages"] + messages
    response = llm.invoke(full_messages)
    
    # Try to parse JSON response
    try:
        # Extract JSON from response (handle markdown code blocks)
        content = response.content.strip()
        if content.startswith("```"):
            # Remove markdown code block markers
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
        
        edit_data = json.loads(content)
        old_code = edit_data.get("old_code", "")
        new_code = edit_data.get("new_code", "")
        
        if not old_code or not new_code:
            raise ValueError("Missing old_code or new_code in JSON response")
        
        # Apply the targeted edit
        fixed_content = apply_edit(original_content, old_code, new_code)
        
        print(f"  ✓ Applied targeted edit ({len(old_code)} → {len(new_code)} chars)")
        
    except (json.JSONDecodeError, ValueError, EditError) as e:
        # Fallback: if JSON parsing or edit application fails, add feedback and retry
        print(f"  ⚠ Targeted edit failed: {e}")
        
        state["retry_count"] += 1
        
        if state["retry_count"] >= state["max_retries"]:
            # Max retries reached, mark as failed
            from debt_zero_agent.models import FailedFix, FixStatus
            failed_fix = FailedFix(
                issue_key=issue.key,
                file_path=file_path,
                status=FixStatus.VALIDATION_ERROR,
                error_message=f"Failed to generate valid edit: {str(e)}",
                llm_provider=state["llm_provider"],
                iterations=state["retry_count"],
            )
            state["failed_fixes"].append(failed_fix)
            state["current_issue_index"] += 1
            return state
        
        # Add feedback for retry
        feedback_msg = f"""Your previous fix attempt failed: {str(e)}

Please try again with a valid JSON response containing "old_code" and "new_code" fields.
Make sure to copy the old_code EXACTLY from the file, including all whitespace."""
        
        state["messages"].append(HumanMessage(content=feedback_msg))
        return state
    
    # Store in state for validation
    state["messages"].append(HumanMessage(content=str(messages[-1].content)))
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
            state["_validation_passed"] = False
            
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
            else:
                # Retries remain - provide feedback
                print(f"  ⚠ Validation failed (attempt {state['retry_count']}/{state['max_retries']})")
                
                # Generate diff of the failed attempt
                failed_diff = generate_diff.invoke({
                    "original": original_content,
                    "modified": fixed_content,
                    "file_path": file_path,
                })
                
                # Build escalating feedback based on retry count
                if state["retry_count"] == 1:
                    strictness = "Be extra careful with syntax."
                elif state["retry_count"] == 2:
                    strictness = "CRITICAL: This is your final attempt. Only change the MINIMUM necessary."
                else:
                    strictness = ""
                
                feedback_msg = f"""Your previous fix attempt had validation errors:

**Errors**: {'; '.join(validation.errors)}

**Your attempted changes**:
```diff
{failed_diff}
```

Please fix these validation errors and try again. {strictness}"""
                
                state["messages"].append(HumanMessage(content=feedback_msg))
            
            return state
    
    # Syntax validation passed - now check diff metrics
    diff = generate_diff.invoke({
        "original": original_content,
        "modified": fixed_content,
        "file_path": file_path,
    })
    
    # Import diff stats function
    from debt_zero_agent.tools import generate_diff_stats
    
    stats = generate_diff_stats(original_content, fixed_content)
    lines_changed = stats["additions"] + stats["deletions"]
    
    # Get thresholds from state (with defaults)
    max_lines_changed = state.get("max_lines_changed", 30)
    max_change_ratio = state.get("max_change_ratio", 0.1)
    
    file_lines = stats["original_lines"]
    change_ratio = lines_changed / max(file_lines, 1)
    
    # Check if changes are excessive
    if lines_changed > max_lines_changed or change_ratio > max_change_ratio:
        print(f"  ⚠ Suspicious diff: {lines_changed} lines changed ({change_ratio:.1%} of file)")
        
        state["retry_count"] += 1
        state["_validation_passed"] = False
        
        if state["retry_count"] >= state["max_retries"]:
            # Max retries reached
            failed_fix = FailedFix(
                issue_key=issue.key,
                file_path=file_path,
                status=FixStatus.VALIDATION_ERROR,
                error_message=f"Excessive changes: {lines_changed} lines ({change_ratio:.1%} of file)",
                llm_provider=state["llm_provider"],
                iterations=state["retry_count"],
            )
            state["failed_fixes"].append(failed_fix)
            state["current_issue_index"] += 1
        else:
            # Provide feedback for retry
            feedback_msg = f"""Your fix changed {lines_changed} lines ({change_ratio:.1%} of the file), which is excessive.

**Diff**:
```diff
{diff}
```

The issue is on line {issue.line or 'N/A'}. Please make a MINIMAL fix that only modifies the affected code.
Focus on changing just the specific line(s) needed to fix the issue."""
            
            state["messages"].append(HumanMessage(content=feedback_msg))
        
        return state
    
    # Validation passed, apply the fix
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
    state["_validation_passed"] = True
    
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
