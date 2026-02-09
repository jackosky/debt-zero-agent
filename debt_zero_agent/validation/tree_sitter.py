"""Multi-language syntax validation using tree-sitter."""

from tree_sitter_language_pack import get_parser

from debt_zero_agent.validation.ast_validator import ValidationResult


def validate_syntax(code: str, language: str) -> ValidationResult:
    """Multi-language syntax validation using tree-sitter.
    
    Args:
        code: Source code to validate
        language: Language identifier (e.g., 'python', 'javascript', 'java')
        
    Returns:
        ValidationResult with syntax errors if found
    """
    try:
        parser = get_parser(language)
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Unsupported language '{language}': {e}"],
            warnings=[],
        )
    
    tree = parser.parse(code.encode())
    errors = []
    
    def find_errors(node):
        """Recursively find ERROR nodes in the syntax tree."""
        if node.type == "ERROR":
            line = node.start_point[0] + 1
            errors.append(f"Syntax error at line {line}")
        for child in node.children:
            find_errors(child)
    
    find_errors(tree.root_node)
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=[],
    )


def detect_language_from_extension(file_path: str) -> str | None:
    """Detect language from file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language identifier or None if unknown
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
    }
    
    for ext, lang in extension_map.items():
        if file_path.endswith(ext):
            return lang
    
    return None
