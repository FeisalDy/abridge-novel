# llm/llm_manager.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """
    Response from an LLM call including text and usage metadata.
    
    This structure enables cost tracking by capturing token counts
    alongside the generated text.
    """
    text: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class LLMManager(ABC):
    """
    Abstract interface for all LLM providers.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Execute the prompt and return generated text.
        """
        pass
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Execute the prompt and return response with usage metadata.
        
        Default implementation calls generate() and estimates tokens.
        Subclasses should override this to provide actual token counts
        from the API response when available.
        """
        text = self.generate(prompt)
        # Default: estimate tokens using character-based heuristic
        # Subclasses should override with actual API-reported counts
        return LLMResponse(
            text=text,
            model=self._get_model_name(),
            input_tokens=self._estimate_tokens(prompt),
            output_tokens=self._estimate_tokens(text),
        )
    
    def _get_model_name(self) -> str:
        """Return the model name. Subclasses should override."""
        return "unknown"
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using character-based heuristic.
        ~3.5 characters per token is a conservative estimate for English.
        """
        return int(len(text) / 3.5)
