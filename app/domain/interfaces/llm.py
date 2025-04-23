# core/interfaces/llm.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMInterface(ABC):
    """Core interface for all LLM modules."""

    @abstractmethod
    async def generate(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            system_prompt: Optional[str] = None,  # Add this
            user_prompt: Optional[str] = None,  # Add this
            **kwargs
    ) -> Dict[str, Any]:
        """Generate text using the model"""
        pass

    async def generate_text(self,  prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            system_prompt: Optional[str] = None,  # Add this
            user_prompt: Optional[str] = None,  # Add this
            **kwargs) -> str:
        return await self.generate(prompt, max_tokens, temperature, top_p, stop_sequences, system_prompt, user_prompt,**kwargs)
