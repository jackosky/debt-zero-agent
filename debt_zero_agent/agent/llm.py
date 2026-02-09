"""LLM factory for dual provider support (OpenAI and Anthropic)."""

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

LLMProvider = Literal["openai", "anthropic"]


def get_llm(provider: LLMProvider = "openai", temperature: float = 0.0) -> BaseChatModel:
    """Get LLM instance based on provider.
    
    Args:
        provider: LLM provider to use
        temperature: Sampling temperature (0.0 = deterministic)
        
    Returns:
        Configured LLM instance
        
    Raises:
        ValueError: If provider is invalid or API key not found
    """
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        return ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=temperature,
            api_key=api_key,
        )
    
    else:
        raise ValueError(f"Invalid provider: {provider}. Must be 'openai' or 'anthropic'")
