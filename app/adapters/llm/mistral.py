# app/adapters/llm/mistral.py
import httpx
import os
from typing import List, Dict, Any, Optional
from app.core.interfaces.llm import LLMInterface
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

    @classmethod
    async def list_available_models(cls) -> List[Dict[str, Any]]:
        """
        List all available Mistral models from Ollama.

        Returns
        -------
        List[Dict[str, Any]]
            List of available models with their details
        """
        api_url = settings.OLLAMA_API_URL
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/tags")
            response.raise_for_status()
            data = response.json()

            # Filter for only Mistral models
            mistral_models = [model for model in data.get("models", [])
                              if "mistral" in model.get("name", "").lower()]

            return mistral_models

    @classmethod
    async def download_model(cls, model_name: str) -> Dict[str, Any]:
        """
        Download a specific Mistral model.

        Parameters
        ----------
        model_name : str
            Name of the model to download

        Returns
        -------
        Dict[str, Any]
            Information about the downloaded model
        """
        api_url = settings.OLLAMA_API_URL
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/pull",
                json={"name": model_name}
            )
            response.raise_for_status()
            return {"status": "success", "model": model_name}