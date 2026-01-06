from llm.llm_config import (
    LLM_PROVIDER,
    SUPPORTED_PROVIDERS,
    CHAPTER_LLM_PROVIDER,
    ARC_LLM_PROVIDER,
    NOVEL_LLM_PROVIDER,
)
from typing import Optional


def _get_provider_for_stage(stage: Optional[str]) -> str:
    """
    Get the LLM provider for a specific pipeline stage.
    
    Stage-specific overrides take precedence over the global LLM_PROVIDER.
    If no override is set for the stage, falls back to global.
    
    Args:
        stage: Pipeline stage name ("chapter", "arc", "novel") or None for global
        
    Returns:
        The provider name to use for this stage
    """
    if stage is None:
        return LLM_PROVIDER
    
    stage_lower = stage.lower()
    
    if stage_lower == "chapter" and CHAPTER_LLM_PROVIDER:
        return CHAPTER_LLM_PROVIDER
    elif stage_lower == "arc" and ARC_LLM_PROVIDER:
        return ARC_LLM_PROVIDER
    elif stage_lower == "novel" and NOVEL_LLM_PROVIDER:
        return NOVEL_LLM_PROVIDER
    
    # Fall back to global provider
    return LLM_PROVIDER


def create_llm(stage: Optional[str] = None):
    """
    Create an LLM instance for the specified pipeline stage.
    
    Stage-specific provider overrides (e.g., ARC_LLM_PROVIDER) take precedence
    over the global LLM_PROVIDER. This enables tiered model selection:
    
    - Chapter (Stage 1): Small local model (7B-9B) for cost efficiency
    - Arc (Stage 2): Mid-tier model for cross-chapter coherence  
    - Novel (Stage 3): Premium model for final global pass
    
    Args:
        stage: Pipeline stage ("chapter", "arc", "novel") or None for global
        
    Returns:
        LLM instance configured for the appropriate provider
    """
    provider = _get_provider_for_stage(stage)
    
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    if provider == "gemini":
        from llm.gemini_llm import GeminiLLM
        return GeminiLLM()

    if provider == "deepseek":
        from llm.deepseek_llm import DeepSeekLLM
        return DeepSeekLLM()

    if provider == "vllm":
        from llm.vllm_openai_llm import VLLMOpenAILLM
        return VLLMOpenAILLM()

    if provider == "cerebras":
        from llm.cerebras_llm import CerebrasLLM
        return CerebrasLLM()

    if provider == "groq":
        from llm.groq_llm import GroqLLM
        return GroqLLM()

    if provider == "copilot":
        from llm.copilot_llm import CopilotLLM
        return CopilotLLM()

    if provider == "ollama":
        from llm.ollama_llm import OllamaLLM
        return OllamaLLM()
    if provider == "openrouter":
        from llm.openrouter_llm import OpenRouterLLM
        return OpenRouterLLM()

    raise ValueError(f"LLM provider {provider} is not supported.")
