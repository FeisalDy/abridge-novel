# llm/llm_manager.py

from abc import ABC, abstractmethod

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
