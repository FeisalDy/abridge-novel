# llm/llm_config.py
import os
from dotenv import load_dotenv
load_dotenv()

SUPPORTED_PROVIDERS = {
    "gemini",
    "deepseek",
    "ollama",
    "vllm",
    "cerebras",
    "groq",
    "copilot",
    "openrouter",
}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "cerebras")
if LLM_PROVIDER not in SUPPORTED_PROVIDERS:
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

# Stage-specific LLM provider overrides (optional)
# If set, overrides the global LLM_PROVIDER for that specific stage.
# This enables tiered model selection:
#   - Chapter: Small local model (7B-9B) for cost efficiency
#   - Arc: Mid-tier model for cross-chapter coherence
#   - Novel: Premium model for final global pass
CHAPTER_LLM_PROVIDER = os.getenv("CHAPTER_LLM_PROVIDER")
ARC_LLM_PROVIDER = os.getenv("ARC_LLM_PROVIDER")
NOVEL_LLM_PROVIDER = os.getenv("NOVEL_LLM_PROVIDER")

# Validate stage-specific providers if set
for stage_name, stage_provider in [
    ("CHAPTER_LLM_PROVIDER", CHAPTER_LLM_PROVIDER),
    ("ARC_LLM_PROVIDER", ARC_LLM_PROVIDER),
    ("NOVEL_LLM_PROVIDER", NOVEL_LLM_PROVIDER),
]:
    if stage_provider is not None and stage_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported {stage_name}: {stage_provider}")

# Shared config
TEMPERATURE = 0.2
MAX_TOKENS = 4096

# Gemini
GEMINI_MODEL = "models/gemini-2.5-flash"

# Ollama (local inference)
# RECOMMENDED 7B-9B MODELS FOR CHAPTER CONDENSATION:
#   - qwen2.5:7b    : Best quality/speed balance, good at following instructions
#   - llama3.1:8b   : Strong general performance
#   - mistral:7b    : Fast inference, good for long context
#   - gemma2:9b     : Google's efficient model
# To use: ollama pull <model_name>
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# DeepSeek
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# vLLM / OpenAI-compatible endpoint
VLLM_API_KEY = "dummy"  # vLLM ignores this
VLLM_MODEL = "Qwen/Qwen2.5-32B-Instruct"

# Cerebras
CEREBRAS_MODEL = "qwen-3-32b"

# Groq
GROQ_MODEL = "qwen/qwen3-32b"

# Copilot
COPILOT_BASE_URL = "https://models.github.ai/inference"
COPILOT_MODEL = "openai/gpt-5-mini"

# OpenRouter (OpenAI-compatible endpoint)
OPENROUTER_MODEL = "qwen/qwen3-4b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"