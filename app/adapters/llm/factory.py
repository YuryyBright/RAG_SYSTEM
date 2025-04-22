# app/adapters/llm/factory.py
from typing import Optional, List, Dict, Any
from app.core.interfaces.llm import LLMInterface

from app.adapters.llm.mistral import MistralLLM
from app.adapters.llm.local import LocalLLM
from app.adapters.llm.manager import LLMModelManager

from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class LLMFactory:
    _model_manager = None

    @classmethod
    def get_model_manager(cls) -> LLMModelManager:
        """
        Get or create the LLM model manager instance.

        Returns
        -------
        LLMModelManager
            The model manager instance
        """
        if cls._model_manager is None:
            cls._model_manager = LLMModelManager()
        return cls._model_manager

    @classmethod
    async def list_available_models(cls, provider: str = "all") -> List[Dict[str, Any]]:
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
        manager = cls.get_model_manager()
        return await manager.list_available_models(provider)

    @classmethod
    async def list_local_models(cls) -> List[Dict[str, Any]]:
        """
        List all locally registered models.

        Returns
        -------
        List[Dict[str, Any]]
            List of locally registered models
        """
        manager = cls.get_model_manager()
        return await manager.list_local_models()

    @classmethod
    async def download_model(cls, model_name: str, provider: str) -> Dict[str, Any]:
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
        manager = cls.get_model_manager()
        return await manager.download_model(model_name, provider)

    @staticmethod
    def get_llm(model_name: Optional[str] = None, provider: Optional[str] = None) -> LLMInterface:
        """
        Instantiate the correct LLM adapter by name and provider.
        Falls back to settings.DEFAULT_MODEL if no name provided.

        Parameters
        ----------
        model_name : Optional[str]
            Name of the model to use
        provider : Optional[str]
            Provider of the model. If not specified, will try to infer from model_name

        Returns
        -------
        LLMInterface
            The instantiated LLM adapter
        """
        name = model_name or settings.LLM_MODEL

        # If provider is not specified, try to infer it
        if not provider:
            # Check if it's in the registry
            manager = LLMFactory.get_model_manager()
            registry = manager.get_registry()

            for model in registry.get("models", []):
                if model["name"] == name:
                    provider = model.get("provider")
                    break

            # If still not found, make a guess based on name prefix
            if not provider:
                if name.startswith("mistral"):
                    provider = "mistral"
                elif "/" in name:  # Likely a HuggingFace model
                    provider = "huggingface"
                # Add other provider detection logic as needed

        # Instantiate the appropriate adapter
        if provider == "mistral":
            return MistralLLM(model_name=name)
        elif provider == "huggingface" or provider == "local":
            return LocalLLM(model_name=name)
        # Add other providers as needed
        # if provider == "openai":
        #     return OpenAIService(model_name=name)
        # if provider == "anthropic":
        #     return AnthropicService(model_name=name)

        logger.error(f"Unknown LLM model or provider: {name}, {provider}")
        raise ValueError(f"Unknown LLM model or provider: {name}")