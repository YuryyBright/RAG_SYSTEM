# app/modules/llm/base.py
from abc import abstractmethod
from typing import Dict, Any, List, Optional

from app.domain.interfaces.llm import LLMInterface
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class BaseLLM(LLMInterface):
    """
    Base class for all LLM implementations.
    Provides common functionality and defines the interface that all LLM handlers must implement.
    """

    def __init__(self, model_name: str, model_path: str):
        """
        Initialize the LLM handler.

        Parameters
        ----------
        model_name : str
            Name of the model
        model_path : str
            Path to the model file or directory
        """
        self.model_name = model_name
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.session = None

        # Load the model
        self._load_model()
        logger.info(f"Initialized {self.__class__.__name__} for model: {model_name}")

    @abstractmethod
    def _load_model(self) -> None:
        """
        Load the model from disk.
        This method should be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _generate_internal(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Internal generation method with model-specific parameters.
        This should be implemented by subclasses.
        """
        pass

    async def generate(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            system_prompt: Optional[str] = None,
            user_prompt: Optional[str] = None,
            **kwargs
    ) -> Dict[str, Any]:
        return await self._generate_internal(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
            **kwargs
        )

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        Subclasses may override this with more accurate implementations.

        Parameters
        ----------
        text : str
            Text to estimate token count for

        Returns
        -------
        int
            Estimated number of tokens
        """
        # Simple fallback estimation: ~3-4 characters per token
        return len(text) // 4