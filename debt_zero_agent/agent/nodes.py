"""LangGraph nodes for the agent workflow."""

from collections import defaultdict

from langchain_core.messages import HumanMessage, SystemMessage

from debt_zero_agent.agent.llm import get_llm
from debt_zero_agent.agent.state import AgentState
from debt_zero_agent.models import FailedFix, FixResult, FixStatus
from debt_zero_agent.prompts.templates import ANALYZE_ISSUE_PROMPT
from debt_zero_agent.tools import generate_diff, generate_diff_stats, read_file, search_code, write_file
from debt_zero_agent.validation import (
    detect_language_from_extension,
    locate_issue,
    validate_syntax,
)


def batch_issues_by_file(issues: list) -> list:
    """Group issues by file and sort bottom-up by line number.
    
    This allows us to:
    1. Read each file only once per batch
    2. Apply fixes from bottom to top (preserving line numbers)
    
    Args:
        issues: List of SonarQubeIssue objects
        
    Returns:
        List of issues sorted by file, then by line number (descending)
    """
    # Group by file
    by_file = defaultdict(list)
    for issue in issues:
        file_path = issue.get_file_path()
        by_file[file_path].append(issue)
    
    # Sort each file's issues bottom-up (highest line number first)
    batched = []
    for file_path in sorted(by_file.keys()):
        file_issues = by_file[file_path]
        # Sort by line number descending (None/0 goes to end)
        file_issues.sort(key=lambda i: i.line or 0, reverse=True)
        batched.extend(file_issues)
    
    return batched


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
    
    # Check cache first (optimization for batched issues)
    file_cache = state.get("file_cache", {})
    if file_path in file_cache:
        content = file_cache[file_path]
    else:
        content = read_file.invoke({
            "repo_path": state["repo_path"],
            "file_path": file_path,
        })
        # Update cache
        file_cache[file_path] = content
        # Ensure state has the updated cache (though dict is mutable)
        state["file_cache"] = file_cache
    
    # Locate issue in AST
    language = detect_language_from_extension(file_path)
    if language and issue.line:
        context = locate_issue(content, language, issue.line)
    else:
        # Fallback if language detection fails
        context = None
    
    # Cross-reference search (Improvement #7)
    cross_ref_context = "N/A"
    if context and context.node_type in ("identifier", "function_definition", "class_definition"):
        try:
            # Extract symbol name (simplistic approach: split by '(' for functions)
            symbol_name = context.node_text.split('(')[0].strip()
            # Only search if symbol name is meaningful (e.g. > 3 chars)
            if len(symbol_name) > 3:
                references = search_code.invoke({
                    "repo_path": state["repo_path"],
                    "query": symbol_name,
                })
                
                # Filter out references in the same file
                cross_refs = [
                    r for r in references
                    if r["file_path"] != file_path
                ][:5]  # Limit to 5 most relevant references
                
                if cross_refs:
                    cross_ref_context = "\n".join(
                        f"  - {r['file_path']}:{r['line_number']}: {r['line_content'].strip()}"
                        for r in cross_refs
                    )
        except Exception as e:
            # Continue without cross-references if search fails
            print(f"  ⚠ Cross-reference search failed: {e}")
            pass
    
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
    llm = get_llm(
        provider=state["llm_provider"],
        model_name=state.get("model_name"),
    )
    
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
        "cross_references": cross_ref_context,
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
    # Check cache first (optimization for batched issues)
    file_cache = state.get("file_cache", {})
    if file_path in file_cache:
        original_content = file_cache[file_path]
    else:
        original_content = read_file.invoke({
            "repo_path": state["repo_path"],
            "file_path": file_path,
        })
        # Update cache
        file_cache[file_path] = original_content
        state["file_cache"] = file_cache
    
    # Use targeted fix prompt for JSON-based edits
    from debt_zero_agent.prompts.templates import TARGETED_FIX_PROMPT
    from debt_zero_agent.tools import EditError, apply_edit
    
    llm = get_llm(
        provider=state["llm_provider"],
        model_name=state.get("model_name"),
    )
    
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
        
        # Handle new format: "edits": [...]
        edits = edit_data.get("edits", [])
        
        # Backward compatibility / fallback for flat structure
        if not edits and "old_code" in edit_data:
            edits = [{
                "file": file_path,
                "old_code": edit_data["old_code"],
                "new_code": edit_data["new_code"]
            }]
            
        if not edits:
             raise ValueError("No edits found in JSON response")
             
        # Apply all edits
        modified_files = {} # path -> content
        
        # Pre-load current file content
        modified_files[file_path] = original_content
        
        # Track total changes for logging
        total_old_chars = 0
        total_new_chars = 0
        
        for edit in edits:
            target_path = edit.get("file", file_path)
            old_code = edit.get("old_code", "")
            new_code = edit.get("new_code", "")
            
            if not old_code or not new_code:
                raise ValueError(f"Missing old_code or new_code in edit for {target_path}")
            
            # If target_path is not in modified_files, load it
            if target_path not in modified_files:
                # Check cache
                file_cache = state.get("file_cache", {})
                if target_path in file_cache:
                    modified_files[target_path] = file_cache[target_path]
                else:
                    # Read from disk
                    content = read_file.invoke({
                        "repo_path": state["repo_path"],
                        "file_path": target_path,
                    })
                    modified_files[target_path] = content
                    # Verify read success? read_file returns content string.
            
            # Apply edit to the accumulating content
            current_content = modified_files[target_path]
            new_content = apply_edit(current_content, old_code, new_code)
            modified_files[target_path] = new_content
            
            total_old_chars += len(old_code)
            total_new_chars += len(new_code)
            
        fixed_content = modified_files[file_path] # Main file content for legacy state
        
        print(f"  ✓ Applied {len(edits)} targeted edits in {len(modified_files)} files ({total_old_chars} → {total_new_chars} chars)")
        
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
    state["_temp_modified_files"] = modified_files
    
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
    modified_files = state.get("_temp_modified_files")
    
    # Fallback for legacy state or single file processing
    if not modified_files:
        fixed_content = state.get("_temp_fixed_content")
        if fixed_content:
            modified_files = {file_path: fixed_content}
        else:
            return state

    # 1. Validate syntax for all modified files
    validation_errors = []
    
    for path, content in modified_files.items():
        language = detect_language_from_extension(path)
        if language:
            validation = validate_syntax(content, language)
            if not validation.valid:
                validation_errors.append(f"File {path}: {'; '.join(validation.errors)}")
                
    if validation_errors:
        # Validation failed
        state["retry_count"] += 1
        state["_validation_passed"] = False
        
        if state["retry_count"] >= state["max_retries"]:
            # Max retries reached
            failed_fix = FailedFix(
                issue_key=issue.key,
                file_path=file_path,
                status=FixStatus.VALIDATION_ERROR,
                error_message="; ".join(validation_errors),
                llm_provider=state["llm_provider"],
                iterations=state["retry_count"],
            )
            state["failed_fixes"].append(failed_fix)
            state["current_issue_index"] += 1
        else:
            # Retries remain - provide feedback
            print(f"  ⚠ Validation failed (attempt {state['retry_count']}/{state['max_retries']})")
            
            error_msg = "\n".join(validation_errors)
            feedback_msg = f"""Your previous fix attempt had validation errors:

**Errors**:
{error_msg}

Please fix these validation errors and try again.
If you modified multiple files, ensure ALL files are syntactically valid."""
            
            state["messages"].append(HumanMessage(content=feedback_msg))
        
        return state

    # 2. Check diff metrics (aggregate)
    total_lines_changed = 0
    max_ratio_exceeded = False
    suspicious_file = ""
    
    # Get thresholds
    max_lines_changed_threshold = state.get("max_lines_changed", 30)
    max_change_ratio_threshold = state.get("max_change_ratio", 0.1)
    
    combined_diff = ""
    
    for path, content in modified_files.items():
        # Get original content from cache (should be there from apply_fix)
        original = state.get("file_cache", {}).get(path, "")
        if not original:
            # Try to read if missing (fallback)
            try:
                original = read_file.invoke({"repo_path": state["repo_path"], "file_path": path})
            except Exception:
                original = ""
        
        stats = generate_diff_stats(original, content)
        total_lines_changed += stats["additions"] + stats["deletions"]
        
        file_lines = stats["original_lines"]
        ratio = (stats["additions"] + stats["deletions"]) / max(file_lines, 1)
        
        if ratio > max_change_ratio_threshold:
            max_ratio_exceeded = True
            suspicious_file = path
            
        # Append to combined diff
        file_diff = generate_diff.invoke({
            "original": original,
            "modified": content,
            "file_path": path,
        })
        combined_diff += f"\n--- {path} ---\n{file_diff}\n"

    # Check if changes are excessive
    if total_lines_changed > max_lines_changed_threshold or max_ratio_exceeded:
        msg = f"Excessive changes: {total_lines_changed} lines changed total."
        if max_ratio_exceeded:
            msg += f" File {suspicious_file} changed > {max_change_ratio_threshold:.1%}."
            
        print(f"  ⚠ {msg}")
        
        state["retry_count"] += 1
        state["_validation_passed"] = False
        
        if state["retry_count"] >= state["max_retries"]:
            failed_fix = FailedFix(
                issue_key=issue.key,
                file_path=file_path,
                status=FixStatus.VALIDATION_ERROR,
                error_message=msg,
                llm_provider=state["llm_provider"],
                iterations=state["retry_count"],
            )
            state["failed_fixes"].append(failed_fix)
            state["current_issue_index"] += 1
        else:
            feedback_msg = f"""Your fix changed {total_lines_changed} lines total, which is excessive.
{msg}

The issue is on line {issue.line or 'N/A'}. Please make a MINIMAL fix."""
            state["messages"].append(HumanMessage(content=feedback_msg))
        
        return state

    # 3. Validation passed - Apply fixes
    state["_validation_passed"] = True
    
    # Write all files
    for path, content in modified_files.items():
        write_file.invoke({
            "repo_path": state["repo_path"],
            "file_path": path,
            "content": content,
            "dry_run": state["dry_run"],
        })
        # Update cache with new content
        state["file_cache"][path] = content
    
    # Record successful fix (using main file info for tracking)
    # Note: 'diff' here is the combined diff of all changes
    fix_result = FixResult(
        issue_key=issue.key,
        file_path=file_path,
        original_content=original_content, # Main file original
        fixed_content=state.get("file_cache", {}).get(file_path, ""),
        diff=combined_diff,
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
