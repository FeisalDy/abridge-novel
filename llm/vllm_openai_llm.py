# llm/vllm_openai_llm.py

import os
from dotenv import load_dotenv
from openai import OpenAI
from llm.llm_manager import LLMManager, LLMResponse
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
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture token usage from vLLM API response.
        
        vLLM uses OpenAI-compatible API with response.usage.
        """
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

        text = text.strip()
        
        # Extract token usage from vLLM response (OpenAI-compatible)
        input_tokens = response.usage.prompt_tokens if response.usage else None
        output_tokens = response.usage.completion_tokens if response.usage else None
        
        return LLMResponse(
            text=text,
            model=VLLM_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return VLLM_MODEL
