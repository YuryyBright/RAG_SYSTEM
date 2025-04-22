# app/adapters/llm/manager.py
import os
import json
from typing import List, Dict, Any, Optional
import httpx
import aiohttp
from urllib.parse import quote

from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class LLMModelManager:
    """
    Manager class for handling LLM model operations like listing and downloading.

    This class provides methods to list available models, download models from various
    providers including Hugging Face, and manage the local model registry.
    """

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.models_dir = os.path.join(self.base_dir, "models", "llm")
        os.makedirs(self.models_dir, exist_ok=True)
        self.registry_path = os.path.join(self.models_dir, "registry.json")

        # Hugging Face API URL
        self.hf_api_url = "https://huggingface.co/api"
        self.hf_token = settings.HUGGINGFACE_TOKEN

        if not os.path.exists(self.registry_path):
            with open(self.registry_path, "w") as f:
                json.dump({"models": []}, f)

        self.sync_local_models()

    def sync_local_models(self) -> None:
        """Ensure that all manually added models in models/llm are in the registry."""
        registry = self.get_registry()
        registered_names = {model["name"] for model in registry.get("models", [])}

        # Scan folder
        for item in os.listdir(self.models_dir):
            item_path = os.path.join(self.models_dir, item)
            if os.path.isdir(item_path) or (item.endswith(".bin") or item.endswith(".safetensors")):
                model_name = os.path.splitext(item)[0] if os.path.isfile(item_path) else item
                if model_name not in registered_names and model_name != "registry.json":
                    # Register new model
                    registry["models"].append({
                        "name": model_name,
                        "provider": "local",
                        "status": "imported"
                    })

        self.update_registry(registry)

    def get_registry(self) -> Dict[str, List]:
        """Get the current model registry."""
        try:
            with open(self.registry_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"models": []}

    def update_registry(self, registry: Dict[str, List]) -> None:
        """Update the model registry file."""
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    async def list_local_models(self) -> List[Dict[str, Any]]:
        """
        List all locally registered models (both downloaded and imported).

        Returns
        -------
        List[Dict[str, Any]]
            List of locally registered models
        """
        registry = self.get_registry()
        return registry.get("models", [])

    async def list_available_models(self, provider: str = "all") -> List[Dict[str, Any]]:
        """
        List all available models from specified provider.

        Parameters
        ----------
        provider : str
            The provider to list models from ('mistral', 'huggingface', 'openai', 'anthropic', 'all')

        Returns
        -------
        List[Dict[str, Any]]
            List of available models
        """
        available_models = []

        if provider in ["mistral", "all"]:
            # Get Mistral models via Ollama
            api_url = settings.OLLAMA_API_URL
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{api_url}/tags")
                    response.raise_for_status()
                    data = response.json()

                    # Add provider information to each model
                    for model in data.get("models", []):
                        model["provider"] = "mistral"
                        available_models.append(model)
            except httpx.HTTPError as e:
                logger.error(f"Error fetching Mistral models: {str(e)}")

        if provider in ["huggingface", "all"]:
            # Get models from Hugging Face
            hf_models = await self._fetch_huggingface_models()
            available_models.extend(hf_models)

        # Add support for other providers as needed
        # if provider in ["openai", "all"]:
        #     # Implementation for OpenAI
        #     pass

        return available_models

    async def _fetch_huggingface_models(self, model_type: str = "text-generation") -> List[Dict[str, Any]]:
        """
        Fetch available models from Hugging Face Hub.

        Parameters
        ----------
        model_type : str
            Type of models to fetch (e.g., 'text-generation')

        Returns
        -------
        List[Dict[str, Any]]
            List of available models from Hugging Face
        """
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"

        try:
            # Use aiohttp for better async performance with HF API
            async with aiohttp.ClientSession() as session:
                # Get popular models with specified task
                async with session.get(
                        f"{self.hf_api_url}/models?sort=downloads&direction=-1&limit=100&filter={model_type}",
                        headers=headers
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()

                        # Format the response to match our expected structure
                        formatted_models = []
                        for model in models_data:
                            formatted_models.append({
                                "name": model.get("id", ""),
                                "provider": "huggingface",
                                "modelId": model.get("id", ""),
                                "downloads": model.get("downloads", 0),
                                "tags": model.get("tags", []),
                                "pipeline_tag": model.get("pipeline_tag", ""),
                                "size": model.get("downloads", 0)  # <-- Correct here
                            })

                        return formatted_models
                    else:
                        logger.error(f"Failed to fetch HF models: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching Hugging Face models: {str(e)}")
            return []

    async def download_model(self, model_name: str, provider: str) -> Dict[str, Any]:
        """
        Download a model from the specified provider.

        Parameters
        ----------
        model_name : str
            Name of the model to download
        provider : str
            Provider of the model ('mistral', 'huggingface', 'openai', 'anthropic')

        Returns
        -------
        Dict[str, Any]
            Information about the download operation
        """
        result = {"status": "error", "message": "Unknown provider"}

        if provider == "mistral":
            api_url = settings.OLLAMA_API_URL
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{api_url}/pull",
                        json={"name": model_name}
                    )
                    response.raise_for_status()

                    # Add to registry
                    registry = self.get_registry()

                    # Check if model already exists in registry
                    existing_model = next((m for m in registry["models"]
                                           if m["name"] == model_name and m["provider"] == provider), None)

                    if not existing_model:
                        registry["models"].append({
                            "name": model_name,
                            "provider": provider,
                            "status": "downloaded"
                        })
                        self.update_registry(registry)

                    result = {"status": "success", "model": model_name, "provider": provider}
            except httpx.HTTPError as e:
                result = {"status": "error", "message": str(e)}

        elif provider == "huggingface":
            try:
                # Use the transformers library to download the model
                from transformers import AutoModel, AutoTokenizer
                import sys
                import os
                from pathlib import Path

                # Create model directory
                model_dir = os.path.join(self.models_dir, model_name.replace("/", "_"))
                os.makedirs(model_dir, exist_ok=True)

                logger.info(f"Downloading model {model_name} from Hugging Face...")

                # Capture download progress
                original_stdout = sys.stdout
                download_log_path = os.path.join(model_dir, "download_log.txt")

                try:
                    with open(download_log_path, 'w') as f:
                        sys.stdout = f

                        # Download the model and tokenizer
                        AutoModel.from_pretrained(model_name, cache_dir=model_dir)
                        AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)

                    sys.stdout = original_stdout

                    # Add to registry
                    registry = self.get_registry()

                    # Check if model already exists in registry
                    existing_model = next((m for m in registry["models"]
                                           if m["name"] == model_name.replace("/", "_") and
                                           m["provider"] == provider), None)

                    if not existing_model:
                        registry["models"].append({
                            "name": model_name.replace("/", "_"),
                            "original_name": model_name,
                            "provider": provider,
                            "status": "downloaded"
                        })
                        self.update_registry(registry)

                    result = {
                        "status": "success",
                        "model": model_name,
                        "provider": provider,
                        "local_path": model_dir
                    }

                except Exception as e:
                    sys.stdout = original_stdout
                    raise e

            except Exception as e:
                result = {"status": "error", "message": str(e)}
                logger.error(f"Error downloading HF model: {str(e)}")

        return result