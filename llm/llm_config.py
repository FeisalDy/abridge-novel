# llm/llm_config.py

LLM_PROVIDER = "deepseek"  # gemini | deepseek | ollama | vllm

# Shared config
TEMPERATURE = 0.2
MAX_TOKENS = 4096

# Gemini
GEMINI_MODEL = "models/gemini-2.5-flash"

# Ollama
OLLAMA_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"

# DeepSeek
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# vLLM / OpenAI-compatible endpoint
VLLM_BASE_URL = "http://YOUR_SERVER_IP:8000/v1"
VLLM_API_KEY = "dummy"  # vLLM ignores this
VLLM_MODEL = "Qwen/Qwen2.5-32B-Instruct"