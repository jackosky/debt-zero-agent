"""Pydantic models for SonarQube API responses."""

from pydantic import BaseModel, Field


class TextRange(BaseModel):
    """Location information for an issue in the source code."""

    startLine: int = Field(..., description="Starting line number (1-indexed)")
    endLine: int = Field(..., description="Ending line number (1-indexed)")
    startOffset: int | None = Field(None, description="Starting character offset")
    endOffset: int | None = Field(None, description="Ending character offset")


class SonarQubeIssue(BaseModel):
    """Represents a single issue from SonarQube."""

    key: str = Field(..., description="Unique issue identifier")
    rule: str = Field(..., description="Rule ID (e.g., 'python:S1234')")
    severity: str = Field(
        ..., description="Issue severity: BLOCKER, CRITICAL, MAJOR, MINOR, INFO"
    )
    component: str = Field(..., description="Component path in SonarQube format")
    message: str = Field(..., description="Human-readable issue description")
    line: int | None = Field(None, description="Line number where issue occurs")
    textRange: TextRange | None = Field(None, description="Precise location range")
    type: str = Field(
        ..., description="Issue type: BUG, VULNERABILITY, CODE_SMELL"
    )
    tags: list[str] = Field(default_factory=list, description="Issue tags")

    def get_file_path(self) -> str:
        """Extract file path from component string.
        
        SonarQube component format: 'project_key:path/to/file.py'
        """
        if ":" in self.component:
            return self.component.split(":", 1)[1]
        return self.component


class IssueSearchResponse(BaseModel):
    """Response from SonarQube api/issues/search endpoint."""

    issues: list[SonarQubeIssue] = Field(
        default_factory=list, description="List of issues"
    )
    total: int = Field(..., description="Total number of issues")
    p: int = Field(1, description="Current page number")
    ps: int = Field(100, description="Page size")

    def filter_by_type(self, *types: str) -> list[SonarQubeIssue]:
        """Filter issues by type (e.g., BUG, VULNERABILITY, CODE_SMELL)."""
        return [issue for issue in self.issues if issue.type in types]
