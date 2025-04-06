# app/adapters/llm/mistral.py
import httpx
from typing import List, Dict, Any, Optional
from api.core.interfaces.llm import LLMInterface
from app.config import settings


class MistralLLM(LLMInterface):
    """
    Implementation of LLM interface using Mistral via Ollama.

    This class provides methods to generate responses using the Mistral
    language model running on Ollama.

    Attributes
    ----------
    model_name : str
        The name of the Mistral model to use.
    api_url : str
        The URL of the Ollama API.
    """

    def __init__(self, model_name: str = "mistral"):
        self.model_name = model_name
        self.api_url = settings.OLLAMA_API_URL

    async def generate(
            self,
            prompt: str,
            context: List[Dict[str, Any]],
            max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response using Mistral LLM.

        Parameters
        ----------
        prompt : str
            The prompt to send to the model.
        context : List[Dict[str, Any]]
            Additional context information.
        max_tokens : Optional[int]
            The maximum number of tokens to generate.

        Returns
        -------
        str
            The generated response.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "max_tokens": max_tokens or 1024,
                    "temperature": 0.1,  # Low temperature for factual responses
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]