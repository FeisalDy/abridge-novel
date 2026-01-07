import os

from llm.llm_config import OPENROUTER_BASE_URL, OPENROUTER_MODEL
from llm.llm_manager import LLMManager, LLMResponse
from openai import OpenAI

from utils import extract_answer
from dotenv import load_dotenv
load_dotenv()

class OpenRouterLLM(LLMManager):
    def __init__(self, api_key:str | None = None):
        key = api_key or os.getenv("OPENENROUTER_API_KEY")
        if not key:
            raise ValueError("OpenRouterLLM requires an API key")
        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
           extra_body={},
            model=OPENROUTER_MODEL,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from OpenRouter LLM.")

        raw = response.choices[0].message.content
        answer = extract_answer(raw)

        return raw

    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture actual token usage from API response.

        OpenAI-compatible APIs return usage info in response.usage.
        """
        response = self.client.chat.completions.create(
           extra_body={},
            model=OPENROUTER_MODEL,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from OpenRouter LLM.")

        raw = response.choices[0].message.content
        answer = extract_answer(raw)

        input_tokens = None
        output_tokens = None

        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        return LLMResponse(
            text=answer,
            model=OPENROUTER_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _get_model_name(self) -> str:
        return OPENROUTER_MODEL