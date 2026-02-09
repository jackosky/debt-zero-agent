"""Models for fix results and agent state."""

from enum import Enum
from pydantic import BaseModel, Field


class FixStatus(str, Enum):
    """Status of a fix attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    SKIPPED = "skipped"


class FixResult(BaseModel):
    """Result of successfully fixing an issue."""

    issue_key: str = Field(..., description="SonarQube issue key")
    file_path: str = Field(..., description="Path to the fixed file")
    original_content: str = Field(..., description="Original file content")
    fixed_content: str = Field(..., description="Modified file content")
    diff: str = Field(..., description="Unified diff of changes")
    status: FixStatus = Field(FixStatus.SUCCESS, description="Fix status")
    llm_provider: str = Field(..., description="LLM used (openai/anthropic)")
    iterations: int = Field(1, description="Number of fix attempts")


class FailedFix(BaseModel):
    """Result of a failed fix attempt."""

    issue_key: str = Field(..., description="SonarQube issue key")
    file_path: str = Field(..., description="Path to the file")
    status: FixStatus = Field(..., description="Failure reason")
    error_message: str = Field(..., description="Error details")
    llm_provider: str = Field(..., description="LLM used (openai/anthropic)")
    iterations: int = Field(0, description="Number of attempts made")
