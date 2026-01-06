"""
ollama_llm.py - Local LLM provider via Ollama

PURPOSE:
    Enable local 7B-9B model inference for chapter-level condensation.
    This supports the pipeline's cost discipline by avoiding cloud API
    calls for Stage 1 (chapter condensation).

RECOMMENDED MODELS (7B-9B class):
    - qwen2.5:7b       - Good balance of quality and speed
    - llama3.1:8b      - Strong general performance
    - mistral:7b       - Fast inference
    - gemma2:9b        - Google's efficient model

USAGE:
    1. Install Ollama: https://ollama.ai
    2. Pull a model: ollama pull qwen2.5:7b
    3. Set environment: LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b
    4. Run pipeline normally

DESIGN:
    - Uses Ollama's REST API (OpenAI-compatible endpoint)
    - Supports token usage tracking via response metadata
    - Falls back to /api/generate if chat endpoint unavailable
"""

import os
import requests
from typing import Optional

from dotenv import load_dotenv

from utils import extract_answer
from llm.llm_manager import LLMManager, LLMResponse
from llm.llm_config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    TEMPERATURE,
    MAX_TOKENS,
)

load_dotenv()


class OllamaLLM(LLMManager):
    """
    Local LLM inference via Ollama.
    
    Ollama provides a simple way to run open-source LLMs locally.
    This implementation uses the REST API for maximum compatibility.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Model name (e.g., "qwen2.5:7b"). Defaults to OLLAMA_MODEL.
            base_url: Ollama server URL. Defaults to OLLAMA_BASE_URL.
        """
        self.model = model or os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
        
        # Validate connection on init
        self._check_connection()
    
    def _check_connection(self) -> None:
        """Verify Ollama server is reachable and model is available."""
        try:
            # Check server is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Check model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Ollama model names can have :latest suffix
            model_base = self.model.split(":")[0]
            available = any(
                m.startswith(model_base) or m == self.model
                for m in model_names
            )
            
            if not available and model_names:
                print(f"[ollama] Warning: Model '{self.model}' not found locally.")
                print(f"[ollama] Available models: {', '.join(model_names)}")
                print(f"[ollama] Run: ollama pull {self.model}")
                
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Start with: ollama serve"
            )
        except Exception as e:
            print(f"[ollama] Warning: Connection check failed: {e}")
    
    def generate(self, prompt: str) -> str:
        """
        Generate text using Ollama's generate API.
        
        Args:
            prompt: The input prompt.
        
        Returns:
            Generated text response.
        """
        response = self._call_api(prompt)
        return response.text
    
    def generate_with_usage(self, prompt: str) -> LLMResponse:
        """
        Generate text and capture token usage metadata.
        
        Ollama provides token counts in the response when available.
        """
        return self._call_api(prompt)
    
    def _call_api(self, prompt: str) -> LLMResponse:
        """
        Call Ollama API and parse response.
        
        Uses /api/generate endpoint which returns token counts.
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
        }
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Ollama request timed out. Model may be too slow or "
                f"input too long. Consider using a smaller model."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API error: {e}")
        
        # Extract response text
        raw_text = data.get("response", "")
        if not raw_text:
            raise RuntimeError("Empty response from Ollama")
        
        # Apply standard answer extraction (strips think blocks, etc.)
        answer = extract_answer(raw_text)
        
        # Extract token counts from Ollama response
        # Ollama provides: prompt_eval_count (input), eval_count (output)
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")
        
        return LLMResponse(
            text=answer,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    
    def _get_model_name(self) -> str:
        """Return the model name for logging/tracking."""
        return self.model


# --------------------------------------------------
# Module Self-Test
# --------------------------------------------------

if __name__ == "__main__":
    print("=== Ollama LLM Test ===\n")
    
    try:
        llm = OllamaLLM()
        print(f"Model: {llm.model}")
        print(f"Base URL: {llm.base_url}")
        
        test_prompt = "In one sentence, what is the capital of France?"
        print(f"\nPrompt: {test_prompt}")
        
        response = llm.generate_with_usage(test_prompt)
        print(f"\nResponse: {response.text}")
        print(f"Input tokens: {response.input_tokens}")
        print(f"Output tokens: {response.output_tokens}")
        
    except Exception as e:
        print(f"Error: {e}")
