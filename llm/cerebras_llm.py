import os
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

from utils import extract_answer
from llm.llm_manager import LLMManager, LLMResponse
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

        raw = response.choices[0].message.content
        answer = extract_answer(raw)

        return answer
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture token usage from Cerebras API response.
        
        Cerebras uses OpenAI-compatible API with response.usage.
        """
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

        raw = response.choices[0].message.content
        answer = extract_answer(raw)
        
        # Extract token usage from Cerebras response (OpenAI-compatible)
        input_tokens = response.usage.prompt_tokens if response.usage else None
        output_tokens = response.usage.completion_tokens if response.usage else None
        
        return LLMResponse(
            text=answer,
            model=CEREBRAS_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return CEREBRAS_MODEL
