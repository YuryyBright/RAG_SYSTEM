# app/modules/llm/factory.py
from typing import List, Dict, Any, Optional, Type
from pathlib import Path

from domain.interfaces.llm import LLMInterface
from app.modules.llm.base import BaseLLM
from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """
    Factory for creating LLM instances based on model type detection.
    All LLMs are loaded from the local storage folder.
    """

    _model_registry = None
    _llm_handlers = {}

    @classmethod
    def register_handler(cls, model_type: str, handler_class: Type[BaseLLM]) -> None:
        """
        Register a handler class for a specific model type.

        Parameters
        ----------
        model_type : str
            The type of model this handler supports (e.g., 'gguf', 'hf', 'onnx')
        handler_class : Type[BaseLLM]
            The class that can handle this model type
        """
        cls._llm_handlers[model_type] = handler_class
        logger.info(f"Registered handler for model type: {model_type}")

    @classmethod
    def get_model_registry(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get or create the model registry with detected local models.

        Returns
        -------
        Dict[str, List[Dict[str, Any]]]
            Dictionary containing the list of available models and their details
        """
        if cls._model_registry is None:
            cls._scan_local_models()
        return cls._model_registry

    @classmethod
    def _scan_local_models(cls) -> None:
        """
        Scan the local models directory to detect available models.
        Auto-detects model types based on file extensions and directory structure.
        """
        models_dir = Path(settings.MODELS_BASE_DIR)
        models = []

        if not models_dir.exists():
            logger.warning(f"Models directory not found: {models_dir}")
            cls._model_registry = {"models": []}
            return

        logger.info(f"Scanning for models in: {models_dir}")

        # First scan for model files with known extensions
        for ext in [".gguf", ".bin", ".onnx", ".safetensors"]:
            for model_file in models_dir.glob(f"**/*{ext}"):
                model_name = model_file.stem
                model_type = ext[1:]  # Remove the dot

                models.append({
                    "name": model_name,
                    "file_path": str(model_file),
                    "type": model_type,
                    "size": model_file.stat().st_size
                })
                logger.debug(f"Found model file: {model_name} ({model_type})")

        # Then scan for directory-based models (like HuggingFace models)
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir():
                # Check if this looks like a HuggingFace model
                if (model_dir / "config.json").exists() or (model_dir / "pytorch_model.bin").exists():
                    model_name = model_dir.name
                    models.append({
                        "name": model_name,
                        "file_path": str(model_dir),
                        "type": "hf",  # HuggingFace format
                        "size": sum(f.stat().st_size for f in model_dir.glob('**/*') if f.is_file())
                    })
                    logger.debug(f"Found HuggingFace model: {model_name}")

        cls._model_registry = {"models": models}
        logger.info(f"Found {len(models)} models in total")

    @classmethod
    def list_available_models(cls) -> List[Dict[str, Any]]:
        """
        List all available models from the local storage.

        Returns
        -------
        List[Dict[str, Any]]
            List of available models with their details
        """
        registry = cls.get_model_registry()
        return registry.get("models", [])

    @classmethod
    def get_llm(cls, model_name: Optional[str] = None) -> LLMInterface:
        """
        Get an LLM instance for the specified model name.
        The factory will automatically detect the model type and create the appropriate handler.

        Parameters
        ----------
        model_name : Optional[str]
            Name of the model to use (if None, will use default from settings)

        Returns
        -------
        LLMInterface
            An LLM interface instance for the requested model

        Raises
        ------
        ValueError
            If the model is not found or the type is not supported
        """
        name = model_name or settings.LLM_MODEL

        # Find the model in the registry
        registry = cls.get_model_registry()
        model_info = None

        for model in registry.get("models", []):
            if model["name"] == name:
                model_info = model
                break

        if not model_info:
            raise ValueError(f"Model not found: {name}")

        # Get the appropriate handler for this model type
        model_type = model_info["type"]
        handler_class = cls._llm_handlers.get(model_type)

        if not handler_class:
            raise ValueError(f"No handler registered for model type: {model_type}")

        # Create and return the handler instance
        return handler_class(model_name=name, model_path=model_info["file_path"])