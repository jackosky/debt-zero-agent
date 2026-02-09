"""Python AST-based syntax validation."""

import ast
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation check."""

    valid: bool
    errors: list[str]
    warnings: list[str]


def validate_python_syntax(code: str) -> ValidationResult:
    """Parse code with ast module, return syntax errors if any.
    
    Args:
        code: Python source code to validate
        
    Returns:
        ValidationResult with syntax check status
    """
    try:
        ast.parse(code)
        return ValidationResult(valid=True, errors=[], warnings=[])
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        return ValidationResult(valid=False, errors=[error_msg], warnings=[])
    except Exception as e:
        return ValidationResult(valid=False, errors=[str(e)], warnings=[])


def compare_ast_structure(original: str, modified: str) -> ValidationResult:
    """Ensure modification doesn't break unrelated code structures.
    
    Compares the AST structure of original and modified code to detect
    unintended changes beyond the fix target.
    
    Args:
        original: Original source code
        modified: Modified source code
        
    Returns:
        ValidationResult indicating if structures are compatible
    """
    warnings = []
    
    try:
        original_tree = ast.parse(original)
        modified_tree = ast.parse(modified)
    except SyntaxError as e:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to parse: {e.msg}"],
            warnings=[],
        )
    
    # Count top-level definitions
    original_funcs = sum(1 for node in ast.walk(original_tree) if isinstance(node, ast.FunctionDef))
    modified_funcs = sum(1 for node in ast.walk(modified_tree) if isinstance(node, ast.FunctionDef))
    
    original_classes = sum(1 for node in ast.walk(original_tree) if isinstance(node, ast.ClassDef))
    modified_classes = sum(1 for node in ast.walk(modified_tree) if isinstance(node, ast.ClassDef))
    
    # Warn if major structural changes detected
    if original_funcs != modified_funcs:
        warnings.append(
            f"Function count changed: {original_funcs} -> {modified_funcs}"
        )
    
    if original_classes != modified_classes:
        warnings.append(
            f"Class count changed: {original_classes} -> {modified_classes}"
        )
    
    return ValidationResult(valid=True, errors=[], warnings=warnings)
