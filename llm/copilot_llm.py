import os
from openai import OpenAI
from dotenv import load_dotenv

from llm.llm_manager import LLMManager
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