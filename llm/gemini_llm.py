# llm/gemini_llm.py

import os
from google import genai
from dotenv import load_dotenv
from llm.llm_manager import LLMManager, LLMResponse
from llm.llm_config import GEMINI_MODEL, TEMPERATURE, MAX_TOKENS

load_dotenv()
class GeminiLLM(LLMManager):
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not found in .env file")

        self.client = genai.Client(api_key=key)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            },
        )

        if not response or not response.text:
            raise RuntimeError("Gemini returned empty response")

        return response.text.strip()
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture token usage from Gemini API response.
        
        Gemini returns usage_metadata with prompt_token_count and candidates_token_count.
        """
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            },
        )

        if not response or not response.text:
            raise RuntimeError("Gemini returned empty response")

        text = response.text.strip()
        
        # Extract token usage from Gemini response
        input_tokens = None
        output_tokens = None
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', None)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', None)
        
        return LLMResponse(
            text=text,
            model=GEMINI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return GEMINI_MODEL
