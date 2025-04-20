# app/core/factories/embedding_factory.py
from typing import Dict, Any, Type
import os

from adapters.embeding.cached_embedding import CachedEmbeddingService
from adapters.embeding.instructor import InstructorEmbedding
from adapters.embeding.open_ai import OpenAIEmbedding
from adapters.embeding.sentence_transformer import SentenceTransformerEmbedding
from core.interfaces.embedding import EmbeddingInterface

from utils.logger_util import get_logger

logger = get_logger(__name__)


class EmbeddingFactory:
    """
    Factory class for creating embedding service instances.

    This factory provides a cleaner way to instantiate different embedding implementations
    based on configuration parameters.
    """

    # Registry of available embedding service implementations
    _registry: Dict[str, Type[EmbeddingInterface]] = {
        "instructor": InstructorEmbedding,
        "openai": OpenAIEmbedding,
        "sentence_transformer": SentenceTransformerEmbedding,
        'cache_embed':CachedEmbeddingService
    }

    @classmethod
    def register_service(cls, name: str, service_class: Type[EmbeddingInterface]) -> None:
        """
        Register a new embedding service implementation.

        Args:
            name: Identifier for the service
            service_class: Implementation class that follows EmbeddingInterface
        """
        cls._registry[name.lower()] = service_class
        logger.info(f"Registered embedding service: {name}")

    @classmethod
    def get_available_services(cls) -> list[str]:
        """
        Get a list of all registered service names.

        Returns:
            List of service names
        """
        return list(cls._registry.keys())

    @classmethod
    async def create(cls, service_name: str, config: Dict[str, Any]) -> EmbeddingInterface:
        """
        Create an embedding service instance based on name and configuration.

        Args:
            service_name: Name of the embedding service to create
            config: Configuration parameters for the service

        Returns:
            An instance of the requested embedding service

        Raises:
            ValueError: If the requested service is not registered
        """
        service_name = service_name.lower()

        if service_name not in cls._registry:
            available = ", ".join(cls.get_available_services())
            raise ValueError(
                f"Unsupported embedding service: {service_name}. "
                f"Available options: {available}"
            )

        service_class = cls._registry[service_name]
        logger.debug(f"Creating embedding service: {service_name}")

        # Filter config to only include parameters accepted by the service's __init__
        service_instance = service_class(**config)

        return service_instance


async def get_embedding_service(settings) -> EmbeddingInterface:
    """
    Factory function to return the appropriate embedding service with optional validation.

    Args:
        settings: Application configuration settings

    Returns:
        Configured embedding service instance
    """
    embedding_service = settings.EMBEDDING_SERVICE.lower()
    logger.debug(f"Initializing embedding service: {embedding_service}")

    # Create configuration dictionary based on service type
    if embedding_service == "instructor":
        config = {
            "model_name": settings.INSTRUCTOR_MODEL_NAME,
            "instruction": settings.EMBEDDING_INSTRUCTION,
            "query_instruction": settings.QUERY_INSTRUCTION,
            "batch_size": settings.EMBEDDING_BATCH_SIZE,
            "device": settings.EMBEDDING_DEVICE
        }
    elif embedding_service == "openai":
        config = {
            "model_name": settings.OPENAI_EMBEDDING_MODEL,
            "api_key": settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"),
            "batch_size": settings.OPENAI_BATCH_SIZE
        }
    elif embedding_service == "sentence_transformer":
        config = {
            "model_name": settings.SENTENCE_TRANSFORMER_MODEL_NAME,
            "batch_size": settings.EMBEDDING_BATCH_SIZE
        }
    else:
        config = {}

    # Create service instance using factory
    service = await EmbeddingFactory.create(embedding_service, config)

    # Validate dimensions if needed
    if hasattr(settings, "EMBEDDING_DIMENSION") and settings.EMBEDDING_DIMENSION:
        await validate_embedding_dimensions(service, expected_dim=settings.EMBEDDING_DIMENSION)

    return service


async def validate_embedding_dimensions(service: EmbeddingInterface, expected_dim: int) -> None:
    """
    Validate that the embedding service produces embeddings of the expected dimension.

    Args:
        service: The embedding service to validate
        expected_dim: Expected embedding dimension

    Raises:
        ValueError: If the embedding dimension doesn't match the expected value
    """
    # Use a simple text to test the embedding dimension
    test_text = "This is a test text for embedding dimension validation."
    test_embedding = await service.get_embedding(test_text)

    actual_dim = len(test_embedding)

    if expected_dim != actual_dim:
        raise ValueError(
            f"Embedding dimension mismatch. Expected: {expected_dim}, "
            f"Actual: {actual_dim}. Please check your configuration."
        )

    logger.debug(f"Embedding dimension validated: {actual_dim}")