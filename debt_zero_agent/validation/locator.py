"""AST-based issue localization using tree-sitter."""

from dataclasses import dataclass

from tree_sitter_language_pack import get_parser


@dataclass
class IssueContext:
    """Rich context around the issue location."""

    node_type: str  # e.g., "function_definition", "call", "identifier"
    node_text: str  # The exact code at this node
    parent_type: str  # Parent node type for context
    parent_text: str  # Parent node code
    siblings: list[str]  # Adjacent statements for broader context
    start_line: int
    end_line: int


def locate_issue(code: str, language: str, line: int, column: int = 0) -> IssueContext:
    """Find the AST node at the given line/column position.
    
    Returns node + parent context for precise targeting.
    
    Args:
        code: Source code
        language: Language identifier (e.g., 'python')
        line: Line number (1-indexed)
        column: Column number (0-indexed)
        
    Returns:
        IssueContext with node and parent information
    """
    parser = get_parser(language)
    tree = parser.parse(code.encode())
    
    def find_deepest_node(node, target_line, target_col):
        """Recursively find the most specific node containing the position."""
        for child in node.children:
            if child.start_point[0] <= target_line <= child.end_point[0]:
                # Check if this child contains the position
                if (
                    child.start_point[0] < target_line < child.end_point[0]
                    or (child.start_point[0] == target_line and child.start_point[1] <= target_col)
                    or (child.end_point[0] == target_line and child.end_point[1] >= target_col)
                ):
                    return find_deepest_node(child, target_line, target_col)
        return node
    
    # Convert to 0-indexed for tree-sitter
    node = find_deepest_node(tree.root_node, line - 1, column)
    parent = node.parent if node.parent else node
    
    # Get sibling nodes for context
    siblings = []
    if parent:
        siblings = [
            child.text.decode("utf-8", errors="ignore")
            for child in parent.children[:5]  # Limit to first 5 siblings
        ]
    
    return IssueContext(
        node_type=node.type,
        node_text=node.text.decode("utf-8", errors="ignore"),
        parent_type=parent.type,
        parent_text=parent.text.decode("utf-8", errors="ignore"),
        siblings=siblings,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
    )
