# app/modules/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from domain.interfaces.llm import LLMInterface
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class BaseLLM(LLMInterface, ABC):
    """
    Abstract base class for all LLM handlers.
    Implements common functionality and defines the interface for LLM handlers.
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
        self._load_model()

    @abstractmethod
    def _load_model(self) -> None:
        """
        Load the model from the specified path.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def generate(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using the model.

        Parameters
        ----------
        prompt : str
            The prompt to generate from
        max_tokens : int
            Maximum number of tokens to generate
        temperature : float
            Sampling temperature (higher = more random)
        top_p : float
            Nucleus sampling probability
        stop_sequences : Optional[List[str]]
            Sequences that will stop generation when encountered
        **kwargs
            Additional model-specific parameters

        Returns
        -------
        Dict[str, Any]
            Generated text and metadata
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the provided text.

        Parameters
        ----------
        text : str
            The text to estimate tokens for

        Returns
        -------
        int
            Estimated number of tokens
        """
        # Default implementation: rough estimate based on whitespace-separated words
        # Subclasses should override this with model-specific token counting
        return len(text.split())