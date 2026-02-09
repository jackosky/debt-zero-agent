"""Prompt templates for agent interactions."""

from langchain_core.prompts import ChatPromptTemplate

# System prompt for the fix agent
SYSTEM_PROMPT = """You are an expert code quality engineer specializing in fixing SonarQube issues.

Your task is to analyze code issues and propose precise, minimal fixes that:
1. Address the specific SonarQube rule violation
2. Maintain code functionality and style
3. Make minimal changes beyond the fix
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
