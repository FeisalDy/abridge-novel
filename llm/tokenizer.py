# llm/tokenizer.py
"""
Token counting utilities for supported LLM providers.

This module provides accurate token counting by using the actual tokenizers
where available, with conservative fallbacks when exact tokenization is not possible.

Supported tokenizer strategies:
- gemini: Uses Google's genai count_tokens API
- OpenAI-compatible (copilot, deepseek, groq, cerebras): Uses tiktoken
- vllm: Uses tiktoken with model-appropriate encoding, or Hugging Face tokenizers
- ollama: Uses tiktoken fallback (conservative estimate)
"""

import os
from functools import lru_cache
from typing import Optional

from llm.llm_config import (
    LLM_PROVIDER,
    GEMINI_MODEL,
    COPILOT_MODEL,
    DEEPSEEK_MODEL,
    GROQ_MODEL,
    CEREBRAS_MODEL,
    VLLM_MODEL,
    OLLAMA_MODEL,
)


# --------------------------------------------------
# Tokenizer cache and initialization
# --------------------------------------------------

# Cached tokenizer instance (initialized lazily)
_tokenizer_instance = None
_tokenizer_type = None


def _get_tiktoken_encoding(model_name: str = "gpt-4"):
    """
    Get tiktoken encoding for a model.
    Falls back to cl100k_base (GPT-4/GPT-3.5) if model not recognized.
    """
    import tiktoken
    
    try:
        # Try to get encoding for specific model
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fall back to cl100k_base (used by GPT-4, GPT-3.5-turbo)
        # This is a reasonable default for most modern LLMs
        return tiktoken.get_encoding("cl100k_base")


def _init_gemini_tokenizer():
    """Initialize Gemini tokenizer using the genai client."""
    from google import genai
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found for token counting")
    
    client = genai.Client(api_key=api_key)
    return client


def _init_huggingface_tokenizer(model_name: str):
    """
    Initialize a Hugging Face tokenizer for models served via vLLM.
    Falls back to tiktoken if the HF tokenizer is not available.
    """
    try:
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(model_name)
    except Exception:
        # Fall back to tiktoken if HF tokenizer unavailable
        return None


@lru_cache(maxsize=1)
def get_tokenizer():
    """
    Get the appropriate tokenizer for the current LLM provider.
    
    Returns a tuple of (tokenizer_type, tokenizer_instance) where:
    - tokenizer_type: "gemini", "tiktoken", "huggingface", or "fallback"
    - tokenizer_instance: The actual tokenizer object
    """
    global _tokenizer_instance, _tokenizer_type
    
    if _tokenizer_instance is not None:
        return _tokenizer_type, _tokenizer_instance
    
    if LLM_PROVIDER == "gemini":
        _tokenizer_type = "gemini"
        _tokenizer_instance = _init_gemini_tokenizer()
        
    elif LLM_PROVIDER == "copilot":
        _tokenizer_type = "tiktoken"
        # Copilot uses OpenAI models (gpt-4, gpt-5-mini, etc.)
        model_base = COPILOT_MODEL.split("/")[-1]  # "openai/gpt-5-mini" -> "gpt-5-mini"
        _tokenizer_instance = _get_tiktoken_encoding(model_base)
        
    elif LLM_PROVIDER == "deepseek":
        _tokenizer_type = "tiktoken"
        # DeepSeek uses a tokenizer similar to GPT-4
        _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
        
    elif LLM_PROVIDER == "groq":
        _tokenizer_type = "tiktoken"
        # Groq hosts various models; use cl100k_base as conservative estimate
        _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
        
    elif LLM_PROVIDER == "cerebras":
        _tokenizer_type = "tiktoken"
        # Cerebras hosts Qwen and other models; tiktoken is a reasonable approximation
        _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
        
    elif LLM_PROVIDER == "vllm":
        # Try to use HuggingFace tokenizer for the specific model
        hf_tokenizer = _init_huggingface_tokenizer(VLLM_MODEL)
        if hf_tokenizer is not None:
            _tokenizer_type = "huggingface"
            _tokenizer_instance = hf_tokenizer
        else:
            # Fall back to tiktoken
            _tokenizer_type = "tiktoken"
            _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
            
    elif LLM_PROVIDER == "ollama":
        _tokenizer_type = "tiktoken"
        # Ollama runs various models locally; use tiktoken as fallback
        _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
        
    else:
        # Unknown provider - use conservative tiktoken fallback
        _tokenizer_type = "tiktoken"
        _tokenizer_instance = _get_tiktoken_encoding("gpt-4")
    
    return _tokenizer_type, _tokenizer_instance


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string using the appropriate tokenizer
    for the current LLM provider.
    
    This provides accurate token counting where possible, with conservative
    fallbacks for providers where exact tokenization is not available.
    
    Args:
        text: The text to count tokens for.
        
    Returns:
        The number of tokens in the text.
    """
    tokenizer_type, tokenizer = get_tokenizer()
    
    if tokenizer_type == "gemini":
        # Use Gemini's count_tokens API
        try:
            response = tokenizer.models.count_tokens(
                model=GEMINI_MODEL,
                contents=text,
            )
            if response.total_tokens is not None:
                return int(response.total_tokens)
            return _fallback_token_estimate(text)
        except Exception:
            # Fall back to character-based estimate on API error
            return _fallback_token_estimate(text)
    
    elif tokenizer_type == "tiktoken":
        # Use tiktoken encoding
        return len(tokenizer.encode(text))  # type: ignore[union-attr]
    
    elif tokenizer_type == "huggingface":
        # Use HuggingFace tokenizer
        return len(tokenizer.encode(text))  # type: ignore[union-attr]
    
    else:
        # Fallback: character-based estimate
        return _fallback_token_estimate(text)


def _fallback_token_estimate(text: str) -> int:
    """
    Conservative character-based token estimate.
    Used as fallback when proper tokenization is not available.
    
    Uses ~3.5 characters per token (conservative for English text).
    """
    return int(len(text) / 3.5)
