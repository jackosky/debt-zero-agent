"""Prompt templates for agent interactions."""

from langchain_core.prompts import ChatPromptTemplate

# System prompt for the fix agent
SYSTEM_PROMPT = """You are an expert code quality engineer specializing in fixing SonarQube issues.

Your task is to analyze code issues and propose precise, minimal fixes that:
1. Address the specific SonarQube rule violation
2. Maintain code functionality and style
3. Make ONLY the minimal changes necessary - do not reformat, reorder, or modify unrelated code
4. Follow language best practices

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

Please analyze this issue and explain:
1. What the issue is
2. Why it's a problem
3. How to fix it

Then propose a fix."""),
])


# Prompt for applying a fix
APPLY_FIX_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Apply the fix for this issue:

**Issue**: {message}
**File**: {file_path}
**Line**: {line}

**Current code**:
```
{current_code}
```

**Proposed fix**: {fix_description}

Generate the complete fixed code for the affected section."""),
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
  "old_code": "the exact lines to replace (copied from the original)",
  "new_code": "the replacement lines"
}}

CRITICAL RULES:
1. Copy the old_code EXACTLY from the file content above - including all whitespace and indentation
2. Include enough context (surrounding lines) to make the match unique
3. Only change what's necessary to fix the issue - do not reformat or modify unrelated code
4. The old_code must appear exactly once in the file

Return ONLY the JSON object, no explanations."""),
])
