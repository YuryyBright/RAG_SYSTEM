# core/interfaces/llm.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class LLMInterface(ABC):
    """
    Core interface for all LLM adapters.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: List[Dict[str, Any]],
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Send `prompt` + optional `context` to the model and return its completion.
        """
        pass

    async def generate_text(self, prompt: str) -> str:
        """
        Convenience method for simple prompt→text calls without external context.
        """
        return await self.generate(prompt, context=[], max_tokens=None)
