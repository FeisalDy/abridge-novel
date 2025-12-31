import os
from openai import OpenAI
from dotenv import load_dotenv

from llm.llm_manager import LLMManager, LLMResponse
from llm.llm_config import COPILOT_BASE_URL, COPILOT_MODEL, TEMPERATURE, MAX_TOKENS
from utils import extract_answer

load_dotenv()
class CopilotLLM(LLMManager):
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GITHUB_TOKEN")
        if not key:
            raise ValueError("GITHUB_TOKEN not found in environment variables.")
        self.client = OpenAI(base_url=COPILOT_BASE_URL, api_key=key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=COPILOT_MODEL,
            max_completion_tokens=MAX_TOKENS,
            stream=False
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from Copilot LLM.")

        raw = response.choices[0].message.content
        answer = extract_answer(raw)

        return raw
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture actual token usage from API response.
        
        OpenAI-compatible APIs return usage info in response.usage.
        """
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=COPILOT_MODEL,
            max_completion_tokens=MAX_TOKENS,
            stream=False
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from Copilot LLM.")

        raw = response.choices[0].message.content
        
        # Extract token usage from API response
        input_tokens = None
        output_tokens = None
        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
        
        return LLMResponse(
            text=raw,
            model=COPILOT_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return COPILOT_MODEL