"""LLM factory for multi-provider support (OpenAI, Anthropic, Google Gemini)."""

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

LLMProvider = Literal["openai", "anthropic", "gemini"]


def get_llm(
    provider: LLMProvider = "openai",
    temperature: float = 0.0,
    model_name: str | None = None,
) -> BaseChatModel:
    """Get LLM instance based on provider.
    
    Args:
        provider: LLM provider to use
        temperature: Sampling temperature (0.0 = deterministic)
        model_name: Specific model name to use (overrides provider default)
        
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
            model=model_name or "gpt-4o",
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Updated to latest stable Sonnet (simulated for 2026 context)
        return ChatAnthropic(
            model=model_name or "claude-sonnet-4-5-20250929",
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Using gemini-2.0-flash (fast and capable)
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-2.0-flash",
            temperature=temperature,
            google_api_key=api_key,
        )
    
    else:
        raise ValueError(f"Invalid provider: {provider}. Must be 'openai', 'anthropic', or 'gemini'")
