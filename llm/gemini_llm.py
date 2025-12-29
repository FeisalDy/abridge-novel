# llm/gemini_llm.py

import os
from google import genai
from dotenv import load_dotenv
from llm.llm_manager import LLMManager
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
