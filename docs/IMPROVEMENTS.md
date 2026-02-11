# Proposed Improvements for Debt-Zero-Agent

## 1. Use Targeted Edits Instead of Full-File Replacement

**Priority: High | Impact: High**

### Problem

In `debt_zero_agent/agent/nodes.py:134-222`, the `apply_fix` node asks the LLM to return the
**complete file content** and then overwrites the entire file via `write_file`. This is the single
largest source of unreliability:

- LLMs frequently introduce subtle unrelated changes — trailing whitespace, reordered imports,
  modified comments, altered string quotes — even when instructed not to.
- The prompt at line 158 says *"Return the COMPLETE file content"*, which means the LLM must
  reproduce potentially thousands of lines perfectly to fix one line. For a 500-line file with a
  one-line fix, 99.8% of the output is wasted tokens that must be reproduced verbatim.
- Larger files are more likely to fail because the LLM's reproduction fidelity degrades with length.

### Proposed Implementation

**Option A: Search-and-replace edit format (recommended)**

Change the LLM output format from "entire file" to a structured edit instruction:

```json
{
  "old_code": "the exact lines to replace (copied from the original)",
  "new_code": "the replacement lines"
}
```

The agent then performs an exact string match of `old_code` in the original file and replaces it
with `new_code`. This is the same approach Claude Code uses internally (its Edit tool), and it
works well because:

- The LLM only needs to output the changed region plus enough surrounding context for unique matching
- Accidental changes to unrelated code are structurally impossible
- Validation can compare just the edit region, not the whole file
- Token usage drops dramatically (especially for large files)

Implementation steps:
1. Update the fix prompt in `nodes.py:158-169` to request JSON-structured edits instead of full file content
2. Add a new function `apply_edit(original_content, old_code, new_code) -> str` in `tools/file_writer.py` that:
   - Finds `old_code` in the original content (exact string match)
   - Validates uniqueness (must match exactly once)
   - Returns the content with the replacement applied
   - Raises an error if `old_code` is not found (triggers retry)
3. Update `validate_fix` to validate only the full file after the edit is applied (tree-sitter still sees the whole file)
4. Update the `APPLY_FIX_PROMPT` in `prompts/templates.py:50-66` to document the new format

**Option B: Line-range replacement**

Have the LLM specify a start line, end line, and replacement text. This is simpler but less robust
because line numbers can drift if the file has been modified by a previous fix.

**Option C: Unified diff format**

Have the LLM output a unified diff. This is well-understood but LLMs sometimes produce malformed
diffs (wrong line numbers, missing context lines). Would require a diff-apply step and error
handling for malformed patches.

### Expected Impact

- Token usage reduction: 60-90% for typical fixes (especially on large files)
- Elimination of "phantom diff" failures where the fix is correct but unrelated lines changed
- Higher success rate on first attempt, reducing retries

---

## 2. Add Semantic Validation, Not Just Syntax Validation

**Priority: High | Impact: High**

### Problem

The current validation pipeline (`validation/tree_sitter.py:8-44`) only checks whether the fixed
code **parses without syntax errors**. This catches broken code but misses:

- Behavioral regressions (the fix compiles but breaks functionality)
- Incomplete fixes (the code parses but still violates the SonarQube rule)
- Structural damage (functions/classes removed or signatures changed)

The Python-specific `compare_ast_structure` in `validation/ast_validator.py` exists but is **never
called** from the main workflow — it's dead code.

### Proposed Implementation

**Layer 1: AST structure comparison (all languages)**

Generalize the existing `compare_ast_structure` (currently Python-only via `ast.parse()`) to use
tree-sitter for all languages:

```python
def compare_structure(original: str, modified: str, language: str) -> ValidationResult:
    """Compare top-level declarations between original and modified code."""
    original_tree = get_parser(language).parse(original.encode())
    modified_tree = get_parser(language).parse(modified.encode())

    # Extract top-level named nodes (functions, classes, methods)
    original_names = extract_declarations(original_tree.root_node)
    modified_names = extract_declarations(modified_tree.root_node)

    warnings = []
    if original_names - modified_names:
        warnings.append(f"Removed declarations: {original_names - modified_names}")
    if modified_names - original_names:
        warnings.append(f"Added declarations: {modified_names - original_names}")

    return ValidationResult(valid=True, errors=[], warnings=warnings)
```

Wire this into `validate_fix` in `nodes.py:225` immediately after the syntax check passes (line 272).
Treat structural changes as warnings that get logged but don't block the fix (some SonarQube rules
legitimately require adding/removing code).

**Layer 2: Test suite execution**

After applying a fix, optionally run the project's test suite:

1. Add a `--run-tests` CLI flag and a `test_command` field to `AgentState`
2. After `write_file` succeeds in `validate_fix`, run the test command via `subprocess.run()`
3. If tests fail, record the failure output, revert the file (restore `_temp_original_content`),
   and either retry or mark as failed
4. Add test output to the retry prompt so the LLM can see what broke

This is the most impactful validation layer because it catches semantic regressions, not just
syntax errors. Implementation in `nodes.py` after line 287:

```python
if test_command and not state["dry_run"]:
    result = subprocess.run(test_command, shell=True, capture_output=True, timeout=120)
    if result.returncode != 0:
        # Revert the file
        write_file.invoke({"repo_path": ..., "file_path": ..., "content": original_content})
        # Feed test output to retry
        state["messages"].append(HumanMessage(
            content=f"Fix caused test failures:\n{result.stderr}\nPlease revise."
        ))
        state["retry_count"] += 1
        return state
```

**Layer 3: SonarQube rule-specific validators**

For common rule categories, add targeted checks:
- **Unused imports** (e.g., `python:S1128`): parse the AST to verify the import was actually removed
- **Cognitive complexity** (e.g., `python:S3776`): compute complexity of the fixed function and
  verify it decreased
- **Duplicate code** (e.g., `common-*:DuplicatedBlocks`): verify the duplication was eliminated

These can be registered in a rule-validator map and invoked when the rule key matches.

---

## 3. Batch Issues by File

**Priority: Medium | Impact: High**

### Problem

Issues are processed sequentially one-at-a-time (`select_next_issue` at `nodes.py:21-49`
increments `current_issue_index` by 1 each time). When multiple issues exist in the same file:

1. The file is read from disk on every iteration (`read_file` at `nodes.py:68-71` in `analyze_issue`
   and again at `nodes.py:149-152` in `apply_fix`) — redundant I/O
2. After fix #1 is written to disk, the line numbers reported by SonarQube for issues #2-#5 in
   the same file may be **wrong** because the fix shifted lines up or down
3. The LLM loses context between iterations — it doesn't know that it already fixed the same file

### Proposed Implementation

**Step 1: Group issues before processing**

In `cli.py`, after loading issues (around line 196), group them by file path:

```python
from collections import defaultdict

def group_issues_by_file(issues):
    """Group issues by file path, sorted by line number within each file."""
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue.get_file_path()].append(issue)
    # Sort issues within each file by line number (bottom-up to preserve line numbers)
    for file_path in grouped:
        grouped[file_path].sort(key=lambda i: i.line or 0, reverse=True)
    return grouped
```

Sorting bottom-up (highest line number first) is critical: fixes applied at the bottom of a file
don't shift the line numbers of issues above them.

**Step 2: Restructure the graph**

Change `AgentState` to track file groups instead of a flat issue list:

```python
class AgentState(TypedDict):
    # Replace flat list with grouped structure
    file_groups: dict[str, list[SonarQubeIssue]]  # file_path → issues
    current_file: str | None
    current_file_issues: list[SonarQubeIssue]
    current_file_content: str  # Read once, updated in memory after each fix
    ...
```

**Step 3: Update the workflow**

Add a `select_next_file` node that picks the next file group, reads the file once, and then
iterates through all issues in that file. After each fix, update `current_file_content` in memory
(don't re-read from disk) and adjust remaining issue line numbers based on the diff delta.

### Expected Impact

- Eliminates redundant file reads (2 reads per issue → 1 read per file)
- Prevents line-number drift for same-file issues
- Enables the LLM to see previously applied fixes in the same file, improving context

---

## 4. Add a Re-Scan Step

**Priority: Medium | Impact: Medium**

### Problem

The agent declares a fix "successful" if it passes tree-sitter syntax validation (`nodes.py:272`).
But a syntactically valid fix may still violate the original SonarQube rule. There's no closed-loop
verification that the issue is actually resolved.

### Proposed Implementation

**Option A: SonarQube API re-check (lightweight)**

After applying all fixes, trigger a SonarQube analysis and check if the issues are resolved:

1. Add a `rescan` node after `finalize` in `graph.py`
2. Use the SonarQube API to trigger an analysis:
   ```
   POST /api/ce/submit?projectKey={key}
   ```
3. Poll the task status until complete:
   ```
   GET /api/ce/task?id={taskId}
   ```
4. Re-fetch the issues and compare against the original list
5. Update `FixResult.status` to `VERIFIED` or `UNVERIFIED`

**Option B: Local SonarQube scanner (comprehensive)**

Run `sonar-scanner` locally if available:

```python
def run_local_scan(repo_path: str, project_key: str) -> dict:
    result = subprocess.run(
        ["sonar-scanner", f"-Dsonar.projectKey={project_key}"],
        cwd=repo_path,
        capture_output=True,
        timeout=300,
    )
    return parse_scanner_output(result)
```

**Option C: Per-fix verification (most granular)**

After each individual fix (not at the end), run the scanner and check if that specific issue
key is resolved. If not, revert and retry with additional context. This is slower but provides
the tightest feedback loop.

### New CLI flags

```
--verify              Run SonarQube re-scan after applying fixes
--scanner-path PATH   Path to sonar-scanner executable (for local verification)
```

### New state fields in `state.py`

```python
verified_fixes: list[FixResult]    # Fixes confirmed resolved by re-scan
unverified_fixes: list[FixResult]  # Fixes that passed syntax but weren't re-scanned
```

---

## 5. Smarter Retry with Error Context

**Priority: Medium | Impact: Medium**

### Problem

When validation fails in `validate_fix` (`nodes.py:248-269`), the retry path sets
`_validation_passed = False` and decrements back to `apply_fix` via the `should_retry` conditional
edge (`graph.py:26-44`). However, the LLM receives **no feedback** about what went wrong.

Looking at the code flow:
1. `validate_fix` detects errors and prints them (line 251)
2. It increments `retry_count` (line 250)
3. It returns state — the conditional edge routes back to `apply`
4. `apply_fix` runs again, but the `messages` list doesn't contain any information about the
   validation failure
5. The LLM essentially generates the same fix again, often failing the same way

The `VALIDATION_FEEDBACK_PROMPT` template exists in `prompts/templates.py:70-87` but is **never
used** in the actual workflow.

### Proposed Implementation

**Step 1: Wire up the feedback prompt**

In `validate_fix`, when validation fails and retries remain, append a feedback message to state
before returning:

```python
# In validate_fix, after line 267 ("Retrying..."), add:
from debt_zero_agent.prompts.templates import VALIDATION_FEEDBACK_PROMPT

feedback_values = {
    "validation_errors": "; ".join(validation.errors),
    "original_code": original_content,
    "fixed_code": fixed_content,
}
feedback_messages = VALIDATION_FEEDBACK_PROMPT.format_messages(**feedback_values)
state["messages"].append(feedback_messages[-1])  # Add the human message with error context
```

**Step 2: Include the diff in retry context**

Show the LLM what it changed (the diff between original and its failed attempt), so it can
understand where its fix went wrong:

```python
failed_diff = generate_diff.invoke({
    "original": original_content,
    "modified": fixed_content,
    "file_path": file_path,
})
state["messages"].append(HumanMessage(
    content=f"Your previous fix attempt produced this diff:\n{failed_diff}\n"
            f"But validation failed with: {'; '.join(validation.errors)}\n"
            f"Please try again, addressing these specific errors."
))
```

**Step 3: Escalate prompt strictness on retries**

On retry #1, use the standard prompt. On retry #2, add more explicit constraints. On retry #3
(final), try a completely different approach — e.g., ask the LLM to fix only the specific line
rather than regenerating a larger block:

```python
if state["retry_count"] == 1:
    fix_prompt += "\nIMPORTANT: Your previous attempt had syntax errors. Be extra careful."
elif state["retry_count"] == 2:
    fix_prompt += "\nCRITICAL: This is your final attempt. Only change the MINIMUM necessary."
```

**Step 4: Use `apply_fix`'s message history**

Modify `apply_fix` to check for validation feedback in the message history and include it in the
LLM invocation. Currently `apply_fix` (line 171) creates a fresh `[SystemMessage, HumanMessage]`
pair, discarding all prior conversation context. Instead, append to existing messages:

```python
# Instead of a fresh message list:
response = llm.invoke(state["messages"] + [HumanMessage(content=fix_prompt)])
```

This lets the LLM see the analysis, its previous attempt, and the validation feedback.

---

## 6. Diff-Based Fix Verification

**Priority: Low | Impact: Medium**

### Problem

There's no guard against the LLM making excessive or unrelated changes. The fix for a single-line
issue might reformat the entire file, rename variables, or restructure logic — and currently it
would pass validation as long as the syntax is valid.

### Proposed Implementation

**Step 1: Compute diff metrics**

The `generate_diff_stats` function already exists in `tools/diff_tool.py` but is never called.
Wire it into `validate_fix` after the diff is generated (line 275-279):

```python
from debt_zero_agent.tools import generate_diff_stats

stats = generate_diff_stats(original_content, fixed_content)
lines_changed = stats["additions"] + stats["deletions"]
```

**Step 2: Define change thresholds**

Set reasonable limits based on the issue scope:

```python
MAX_LINES_CHANGED = 30        # Absolute maximum for any single fix
SUSPICIOUS_RATIO = 0.1        # If >10% of the file is changed, it's suspicious

file_lines = original_content.count('\n')
ratio = lines_changed / max(file_lines, 1)

if lines_changed > MAX_LINES_CHANGED or ratio > SUSPICIOUS_RATIO:
    print(f"  ⚠ Suspicious diff: {lines_changed} lines changed ({ratio:.1%} of file)")
    # Treat as validation failure and retry with stricter prompt
    state["retry_count"] += 1
    state["messages"].append(HumanMessage(
        content=f"Your fix changed {lines_changed} lines, but the issue is on a single line. "
                f"Please make a MINIMAL fix that only modifies the affected code."
    ))
    return state
```

**Step 3: Proximity check**

Verify that the changes are near the reported issue line:

```python
import re

diff_lines = diff.split('\n')
changed_line_numbers = []
current_line = 0
for line in diff_lines:
    hunk_match = re.match(r'^@@ -\d+,?\d* \+(\d+),?\d* @@', line)
    if hunk_match:
        current_line = int(hunk_match.group(1))
    elif line.startswith('+') and not line.startswith('+++'):
        changed_line_numbers.append(current_line)
        current_line += 1
    elif line.startswith('-') and not line.startswith('---'):
        pass  # Deletion doesn't increment
    else:
        current_line += 1

issue_line = issue.line or 0
if changed_line_numbers:
    min_distance = min(abs(ln - issue_line) for ln in changed_line_numbers)
    if min_distance > 20:
        print(f"  ⚠ Changes are {min_distance} lines away from issue (line {issue_line})")
```

**Step 4: Make thresholds configurable**

Add CLI flags:
```
--max-lines-changed N    Maximum lines a single fix can change (default: 30)
--max-change-ratio F     Maximum file change ratio (default: 0.1)
```

---

## 7. Support for Multi-File Fixes

**Priority: Low | Impact: Medium**

### Problem

The current workflow assumes every SonarQube issue can be fixed by modifying a single file. However,
many real-world issues require cross-file understanding or changes:

- **Unused import** (`python:S1128`): the import might be used in another file via `from x import *`
- **Missing type hints** (`python:S5765`): fixing a method signature may require updating all callers
- **Duplicate code** (`common-*:DuplicatedBlocks`): the fix is to extract a shared function, which
  means modifying multiple files
- **Interface violations**: adding a missing method to satisfy an interface defined elsewhere

The `code_search` tool exists in `tools/code_search.py` but is never used in the fix pipeline — it's
registered as a LangChain tool (`@tool` decorator) but never invoked from any node.

### Proposed Implementation

**Step 1: Add cross-reference search to analysis**

In `analyze_issue` (`nodes.py:52-131`), after locating the issue in the AST, search for related
code in other files:

```python
# After line 77 (locate_issue), add cross-reference search
if context and context.node_type in ("identifier", "function_definition", "class_definition"):
    # Search for usages of the identified symbol across the codebase
    symbol_name = context.node_text.split('(')[0].strip()
    references = search_code.invoke({
        "repo_path": state["repo_path"],
        "query": symbol_name,
    })

    # Filter to relevant references (not the issue file itself)
    cross_refs = [
        r for r in references
        if r["file_path"] != file_path
    ][:5]  # Limit to 5 most relevant

    if cross_refs:
        cross_ref_context = "\n".join(
            f"  - {r['file_path']}:{r['line_number']}: {r['line_content']}"
            for r in cross_refs
        )
        # Include in the analysis prompt
        prompt_values["cross_references"] = cross_ref_context
```

**Step 2: Update prompts to include cross-references**

Add cross-reference context to `ANALYZE_ISSUE_PROMPT` in `prompts/templates.py`:

```
**Cross-references** (usages in other files):
{cross_references}

Consider these usages when proposing your fix. If the fix requires changes to other files,
list them explicitly.
```

**Step 3: Support multi-file fix output**

Extend the fix format to allow multiple file edits:

```json
{
  "edits": [
    {"file": "src/main.py", "old_code": "...", "new_code": "..."},
    {"file": "src/utils.py", "old_code": "...", "new_code": "..."}
  ]
}
```

Update `validate_fix` to validate all modified files and `write_file` to write all of them
(or none, if any validation fails — atomic multi-file writes).

**Step 4: Add a dependency-aware skip**

If the analysis reveals that the fix requires changes to files outside the repository (e.g.,
third-party libraries), skip the issue with a clear explanation rather than attempting a doomed fix.

---

## 8. Upgrade LLM Models

**Priority: Low | Impact: Low**

### Problem

The hardcoded model versions in `agent/llm.py` are outdated:

| Provider  | Current Model (line)                  | Latest Available          |
|-----------|---------------------------------------|---------------------------|
| OpenAI    | `gpt-4o` (lines 62, 76)              | `gpt-4o` (current)       |
| Anthropic | `claude-3-5-sonnet-20241022` (93,109) | `claude-sonnet-4-5-20250929` |
| Gemini    | `gemini-2.0-flash` (line 121)         | `gemini-2.0-flash` (current) |

### Proposed Implementation

**Step 1: Make models configurable**

Add a `--model` CLI flag and environment variable fallback:

```python
# In cli.py, add argument:
parser.add_argument(
    "--model",
    help="Specific model to use (overrides provider default). "
         "Examples: gpt-4o, claude-sonnet-4-5-20250929, gemini-2.0-flash",
)

# In state.py, add field:
model_name: NotRequired[str]  # Override default model
```

**Step 2: Update default models in llm.py**

```python
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-2.0-flash",
}

def get_llm(provider, temperature=0.0, model_override=None):
    model = model_override or DEFAULT_MODELS[provider]
    ...
```

**Step 3: Add model validation**

When a user specifies a model, validate that it's compatible with the selected provider (e.g.,
don't allow `gpt-4o` with `--llm anthropic`).

---

## 9. Add Git Integration

**Priority: Medium | Impact: Medium**

### Problem

Currently fixes are written directly to the working tree with no version control integration
(`file_writer.py:34`). This means:

- Fixes can't be easily reviewed as a group
- There's no way to roll back a bad fix without manual `git checkout`
- Fixes aren't attributable (who/what made the change?)
- No PR workflow for team review before merging

### Proposed Implementation

**Step 1: Create a git operations module**

```python
# debt_zero_agent/tools/git_ops.py

import subprocess
from datetime import datetime

def create_fix_branch(repo_path: str) -> str:
    """Create a new branch for fixes."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"fix/sonarqube-{timestamp}"
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo_path, check=True
    )
    return branch_name

def commit_fix(repo_path: str, file_path: str, issue_key: str, message: str) -> str:
    """Commit a single fix with a descriptive message."""
    subprocess.run(["git", "add", file_path], cwd=repo_path, check=True)
    commit_msg = f"fix({issue_key}): {message}\n\nAutomated fix by debt-zero-agent"
    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=repo_path, check=True
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path, capture_output=True, text=True
    )
    return result.stdout.strip()

def create_pull_request(repo_path: str, branch: str, fixes: list, failures: list) -> str:
    """Create a PR using GitHub CLI (gh)."""
    body = f"## Automated SonarQube Fixes\n\n"
    body += f"**{len(fixes)}** issues fixed, **{len(failures)}** failed\n\n"
    body += "### Fixed Issues\n"
    for fix in fixes:
        body += f"- {fix.issue_key}: {fix.file_path}\n"

    result = subprocess.run(
        ["gh", "pr", "create", "--title",
         f"fix: resolve {len(fixes)} SonarQube issues",
         "--body", body],
        cwd=repo_path, capture_output=True, text=True
    )
    return result.stdout.strip()  # PR URL
```

**Step 2: Wire into the workflow**

Add CLI flags:
```
--git-branch           Create a branch and commit each fix (default: off)
--create-pr            Create a pull request after all fixes (implies --git-branch)
--commit-per-fix       One commit per fix (default) vs. one commit for all fixes
```

In `nodes.py`:
- In `select_next_issue` (first call only): create the fix branch
- In `validate_fix` (after successful write): commit the fix
- In `finalize`: optionally create a PR

**Step 3: Add rollback capability**

If a fix causes test failures (see improvement #2), revert the commit:

```python
def revert_last_commit(repo_path: str):
    subprocess.run(["git", "revert", "HEAD", "--no-edit"], cwd=repo_path, check=True)
```

**Step 4: Stash/restore dirty state**

Before creating a branch, stash any uncommitted changes in the working tree. After the agent
finishes, restore them:

```python
def stash_changes(repo_path: str) -> bool:
    """Stash uncommitted changes. Returns True if anything was stashed."""
    result = subprocess.run(
        ["git", "stash", "push", "-m", "debt-zero-agent: pre-fix stash"],
        cwd=repo_path, capture_output=True, text=True
    )
    return "No local changes" not in result.stdout
```

---

## 10. Parallelize Independent Fixes

**Priority: Low | Impact: Medium**

### Problem

The current graph is strictly sequential: `select_next → analyze → apply → validate → select_next`.
Each issue takes 5-15 seconds of LLM processing. For 50 issues, that's 4-12 minutes of serial
execution. Issues in different files are independent and could run concurrently.

### Proposed Implementation

**Step 1: Group issues by file (prerequisite: Improvement #3)**

Issues in the same file must remain sequential. Issues in different files are independent.

**Step 2: Use LangGraph's `Send` API for fan-out**

LangGraph supports dynamic parallelism via the `Send` primitive:

```python
from langgraph.constants import Send

def fan_out_files(state: AgentState) -> list[Send]:
    """Fan out to process each file group in parallel."""
    sends = []
    for file_path, issues in state["file_groups"].items():
        sends.append(Send("process_file", {
            "file_path": file_path,
            "issues": issues,
            "repo_path": state["repo_path"],
            "llm_provider": state["llm_provider"],
            "dry_run": state["dry_run"],
            "max_retries": state["max_retries"],
        }))
    return sends
```

**Step 3: Add concurrency limits**

LLM API rate limits will throttle unbounded parallelism. Add a semaphore:

```python
import asyncio

# In cli.py or graph.py:
MAX_CONCURRENT_FILES = 3  # Process at most 3 files simultaneously
semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILES)
```

Add a CLI flag:
```
--concurrency N    Maximum parallel file processing (default: 3)
```

**Step 4: Aggregate results**

After all parallel branches complete, merge their `successful_fixes` and `failed_fixes` lists
into the parent state for the `finalize` node.

**Step 5: Handle shared state**

If using git integration (improvement #9), commits must be serialized. Use a lock:

```python
import threading
git_lock = threading.Lock()

def commit_fix_safe(repo_path, file_path, issue_key, message):
    with git_lock:
        return commit_fix(repo_path, file_path, issue_key, message)
```

### Expected Impact

- 3x-5x wall-clock speedup for large issue sets (with concurrency=3-5)
- No impact on fix quality (parallelism is across independent files)
- Requires careful handling of shared resources (git, file system, LLM rate limits)
