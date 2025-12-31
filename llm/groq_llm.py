import os
from groq import Groq
from dotenv import load_dotenv

from llm.llm_manager import LLMManager, LLMResponse
from llm.llm_config import TEMPERATURE, MAX_TOKENS, GROQ_MODEL

from utils import extract_answer
load_dotenv()

class GroqLLM(LLMManager):
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.client = Groq(api_key=key)

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            model=GROQ_MODEL,
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
            top_p=0.95,
            reasoning_effort="default",
            stream=False
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from Groq LLM.")

        raw = response.choices[0].message.content
        answer = extract_answer(raw)

        return answer
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture token usage from Groq API response.
        
        Groq uses OpenAI-compatible API with response.usage.
        """
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            model=GROQ_MODEL,
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
            top_p=0.95,
            reasoning_effort="default",
            stream=False
        )

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("No response from Groq LLM.")

        raw = response.choices[0].message.content
        answer = extract_answer(raw)
        
        # Extract token usage from Groq response (OpenAI-compatible)
        input_tokens = response.usage.prompt_tokens if response.usage else None
        output_tokens = response.usage.completion_tokens if response.usage else None
        
        return LLMResponse(
            text=answer,
            model=GROQ_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return GROQ_MODEL
