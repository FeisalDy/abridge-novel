import os
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

from llm.llm_manager import LLMManager
from llm.llm_config import CEREBRAS_MODEL, TEMPERATURE, MAX_TOKENS

load_dotenv()


class CerebrasLLM(LLMManager):
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not key:
            raise ValueError(
                "Cerebras API key must be provided either as an argument or via the CEREBRAS_API_KEY environment variable.")
        self.client = Cerebras(api_key=key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            model=CEREBRAS_MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=1,
            stream=False
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from Cerebras LLM.")

        return response.choices[0].message.content.strip()
