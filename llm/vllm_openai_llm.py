# llm/vllm_openai_llm.py

from openai import OpenAI

from llm.llm_manager import LLMManager
from llm.llm_config import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    VLLM_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
)


class VLLMOpenAILLM(LLMManager):
    def __init__(self):
        self.client = OpenAI(
            api_key=VLLM_API_KEY,
            base_url=VLLM_BASE_URL,
        )

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("vLLM returned empty response")

        return text.strip()
