# core/interfaces/llm.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMInterface(ABC):
    """Core interface for all LLM modules."""

    @abstractmethod
    async def generate(self, prompt: str, context: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> str:
        pass

    async def generate_text(self, prompt: str) -> str:
        return await self.generate(prompt, context=[], max_tokens=None)
