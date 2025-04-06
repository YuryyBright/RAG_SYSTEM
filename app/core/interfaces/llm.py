
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMInterface(ABC):
    """
    Interface for large language models.

    This interface defines the contract for generating responses from a large language model
    based on a given prompt and context.

    Methods
    -------
    generate(prompt: str, context: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> str
        Asynchronously generates a response based on the provided prompt and context.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: List[Dict[str, Any]],
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response based on the provided prompt and context.

        Parameters
        ----------
        prompt : str
            The input text to generate a response for.
        context : List[Dict[str, Any]]
            A list of dictionaries containing additional context information.
        max_tokens : Optional[int], optional
            The maximum number of tokens to generate in the response (default is None).

        Returns
        -------
        str
            The generated response as a string.
        """
        pass