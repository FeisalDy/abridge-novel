import os
from openai import OpenAI
from dotenv import load_dotenv
from llm.llm_manager import LLMManager, LLMResponse
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
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture actual token usage from API response.
        """
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

        text = response.choices[0].message.content.strip()
        
        # Extract token usage from API response
        input_tokens = None
        output_tokens = None
        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
        
        return LLMResponse(
            text=text,
            model=DEEPSEEK_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        return DEEPSEEK_MODEL
