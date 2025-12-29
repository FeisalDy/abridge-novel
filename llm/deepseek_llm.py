import os
from openai import OpenAI
from dotenv import load_dotenv
from llm.llm_manager import LLMManager
from llm.llm_config import DEEPSEEK_MODEL, DEEPSEEK_BASE_URL,TEMPERATURE

load_dotenv()

class DeepSeekLLM(LLMManager):
    def __init__(self, api_key:str | None = None):
        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY not found in .env file")
        self.client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)


    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "You are acting as a disciplined literary editor"},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
        )

        if not response or not response.choices or not response.choices[0].message.content:
            raise RuntimeError("DeepSeek returned empty response")

        return response.choices[0].message.content.strip()
