"""Prompt templates for agent interactions."""

from langchain_core.prompts import ChatPromptTemplate

# System prompt for the fix agent
SYSTEM_PROMPT = """You are an expert code quality engineer specializing in fixing SonarQube issues.

Your task is to analyze code issues and propose precise, minimal fixes that:
1. Address the specific SonarQube rule violation
2. Maintain code functionality and style
3. Make ONLY the minimal changes necessary - do not reformat, reorder, or modify unrelated code
4. Follow language best practices
5. SAFETY FIRST: Do not introduce new bugs or regressions. If a fix is risky, explain why.

You have access to tools for:
- Reading files and specific line ranges
- Searching the codebase for patterns
- Understanding AST context around issues

Always provide clear explanations for your fixes."""


# Prompt for analyzing an issue
ANALYZE_ISSUE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Analyze this SonarQube issue:

**Issue Key**: {issue_key}
**Rule**: {rule}
**Severity**: {severity}
**Type**: {type}
**File**: {file_path}
**Line**: {line}
**Message**: {message}

**AST Context**:
- Node type: {node_type}
- Node text: {node_text}
- Parent type: {parent_type}

**Cross-references** (usages in other files):
{cross_references}

Please analyze this issue step-by-step:
1. **Understanding**: What is the root cause of the issue?
2. **Impact**: Why is it a problem?
3. **Strategy**: How should it be fixed safely? Consider side effects on cross-references.
4. **Proposal**: Describe the fix in detail.

Then propose a concrete fix logic."""),
])




# Prompt for validation feedback
VALIDATION_FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """The proposed fix has validation errors:

{validation_errors}

**Original code**:
```
{original_code}
```

**Your fix**:
```
{fixed_code}
```

Please revise the fix to address these validation errors."""),
])


# Prompt for targeted fix (search-and-replace format)
TARGETED_FIX_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Based on the previous analysis, generate a targeted fix for this issue.

**Issue**: {message}
**File**: {file_path}
**Line**: {line}

**File content**:
```
{file_content}
```

Return your fix as a JSON object with the following structure:
{{
  "edits": [
    {{
      "file": "{file_path}",  # The file path to modify
      "old_code": "the exact lines to replace (copied from the original)",
      "new_code": "the replacement lines"
    }}
  ]
}}

CRITICAL RULES:
1. **EXACT MATCH**: `old_code` must match the file content EXACTLY, character-for-character, including all whitespace and indentation.
2. **UNIQUENESS**: Include enough lines of context around the change to ensure `old_code` appears exactly once in the file.
3. **NO REFORMATTING**: Do not change indentation or style of lines you are not fixing.
4. **NO PLACEHOLDERS**: Do NOT use `// ...` or `...` to skip code in `old_code`. You must provide the full block to be replaced.
5. **MULTI-FILE**: If necessary, include multiple objects in the "edits" array.
6. **JSON ONLY**: Return strictly valid JSON. No markdown fencing if possible, but code blocks are accepted.
"""),
])
