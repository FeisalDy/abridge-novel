from llm.llm_config import LLM_PROVIDER

def create_llm():
    if LLM_PROVIDER == "gemini":
        from llm.gemini_llm import GeminiLLM
        return GeminiLLM()

    if LLM_PROVIDER == "deepseek":
        from llm.deepseek_llm import DeepSeekLLM
        return DeepSeekLLM()

    if LLM_PROVIDER == "vllm":
        from llm.vllm_openai_llm import VLLMOpenAILLM
        return VLLMOpenAILLM()

    if LLM_PROVIDER == "cerebras":
        from llm.cerebras_llm import CerebrasLLM
        return CerebrasLLM()

    if LLM_PROVIDER == "ollama":
        raise ValueError("Ollama is not implemented yet.")

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
