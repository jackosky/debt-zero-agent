"""Test Gemini LLM support."""

import os
from unittest.mock import patch

import pytest
from debt_zero_agent.agent import get_llm


def test_get_llm_gemini():
    """Test getting Gemini LLM."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        llm = get_llm("gemini")
        assert llm is not None
        assert "gemini" in llm.model.lower()


def test_get_llm_gemini_missing_key():
    """Test error when Gemini API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            get_llm("gemini")
