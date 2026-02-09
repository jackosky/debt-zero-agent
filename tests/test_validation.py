"""Unit tests for validation modules."""

import pytest
from debt_zero_agent.validation import (
    IssueContext,
    ValidationResult,
    compare_ast_structure,
    detect_language_from_extension,
    locate_issue,
    validate_python_syntax,
    validate_syntax,
)


# AST Validator Tests


def test_validate_python_syntax_valid():
    """Test validation of valid Python code."""
    code = """
def hello():
    print("Hello, world!")
"""
    result = validate_python_syntax(code)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_python_syntax_invalid():
    """Test validation of invalid Python code."""
    code = """
def hello(
    print("Missing closing paren")
"""
    result = validate_python_syntax(code)
    assert result.valid is False
    assert len(result.errors) > 0


def test_compare_ast_structure_same():
    """Test AST comparison with identical structure."""
    original = """
def foo():
    x = 1
    return x
"""
    modified = """
def foo():
    x = 2  # Changed value
    return x
"""
    result = compare_ast_structure(original, modified)
    assert result.valid is True
    assert len(result.warnings) == 0


def test_compare_ast_structure_added_function():
    """Test AST comparison when function is added."""
    original = """
def foo():
    return 1
"""
    modified = """
def foo():
    return 1

def bar():
    return 2
"""
    result = compare_ast_structure(original, modified)
    assert result.valid is True
    assert len(result.warnings) > 0
    assert "Function count changed" in result.warnings[0]


# Tree-sitter Tests


def test_validate_syntax_python_valid():
    """Test tree-sitter validation with valid Python."""
    code = """
def greet(name):
    print(f"Hello, {name}!")
"""
    result = validate_syntax(code, "python")
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_syntax_python_invalid():
    """Test tree-sitter validation with invalid Python."""
    code = """
def greet(name
    print(f"Hello, {name}!")
"""
    result = validate_syntax(code, "python")
    assert result.valid is False
    assert len(result.errors) > 0


def test_detect_language_from_extension():
    """Test language detection from file extensions."""
    assert detect_language_from_extension("main.py") == "python"
    assert detect_language_from_extension("app.js") == "javascript"
    assert detect_language_from_extension("Main.java") == "java"
    assert detect_language_from_extension("unknown.xyz") is None


# Locator Tests


def test_locate_issue_function_def():
    """Test locating issue in function definition."""
    code = """
def calculate(x, y):
    result = x + y
    return result
"""
    # Line 2 (0-indexed line 1) is the function definition
    context = locate_issue(code, "python", line=2, column=0)
    
    assert context is not None
    assert context.start_line >= 1
    assert context.end_line >= context.start_line
    assert len(context.node_text) > 0


def test_locate_issue_variable():
    """Test locating issue at variable assignment."""
    code = """
x = 10
y = 20
z = x + y
"""
    # Line 2 is the variable assignment
    context = locate_issue(code, "python", line=2, column=0)
    
    assert context is not None
    assert context.node_text is not None
    assert context.parent_text is not None


def test_locate_issue_with_siblings():
    """Test that sibling context is captured."""
    code = """
def foo():
    a = 1
    b = 2
    c = 3
    return a + b + c
"""
    context = locate_issue(code, "python", line=3, column=4)
    
    assert context is not None
    assert len(context.siblings) > 0


def test_issue_context_dataclass():
    """Test IssueContext dataclass creation."""
    context = IssueContext(
        node_type="identifier",
        node_text="x",
        parent_type="assignment",
        parent_text="x = 10",
        siblings=["y = 20", "z = 30"],
        start_line=5,
        end_line=5,
    )
    
    assert context.node_type == "identifier"
    assert context.start_line == 5
    assert len(context.siblings) == 2
