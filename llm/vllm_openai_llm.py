# llm/vllm_openai_llm.py

import os
from dotenv import load_dotenv
from openai import OpenAI
from llm.llm_manager import LLMManager
from llm.llm_config import (
    VLLM_API_KEY,
    VLLM_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
)

load_dotenv()

class VLLMOpenAILLM(LLMManager):
    def __init__(self):
        vllm_base_url = os.getenv("VLLM_BASE_URL")

        if not vllm_base_url:
            raise ValueError("VLLM_BASE_URL environment variable is not set")

        self.client = OpenAI(
            api_key=VLLM_API_KEY,
            base_url=vllm_base_url,
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
