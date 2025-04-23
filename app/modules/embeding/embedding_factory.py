# app/factories/embedding_factory.py


from modules.embeding.instructor import InstructorEmbedding
from modules.embeding.open_ai import OpenAIEmbedding
from modules.embeding.sentence_transformer import SentenceTransformerEmbedding
from config import settings
from domain.interfaces.embedding import EmbeddingInterface

from utils.logger_util import get_logger

logger = get_logger(__name__)


async def validate_embedding_dimensions(service: EmbeddingInterface, expected_dim: int=768) -> None:
    """
    Validate that the embedding service produces vectors with the expected dimensions.

    Args:
        service: The embedding service to validate
        expected_dim: The expected dimensionality of embeddings

    Raises:
        ValueError: If dimensions don't match expected value
    """
    # Sample text for validation
    sample_text = "This is a test document for embedding dimension validation."

    try:
        # Generate a sample embedding
        sample_embedding = await service.get_embedding(sample_text)
        actual_dim = len(sample_embedding)

        if actual_dim != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}"
            )

        logger.info(f"✅ Embedding dimensions validated: {actual_dim}")
    except Exception as e:
        logger.error(f"❌ Embedding validation failed: {str(e)}")
        raise


async def get_embedding_service() -> EmbeddingInterface:
    """
    Factory function to return the appropriate embedding service with optional caching.

    Returns:
        The configured embedding service implementing the EmbeddingInterface

    Raises:
        ValueError: If the requested service is not supported or validation fails
    """
    embedding_service = settings.EMBEDDING_SERVICE.lower()
    logger.debug(f"Initializing embedding service: {embedding_service}")

    if embedding_service == "instructor":
        service = InstructorEmbedding(
            model_name=settings.INSTRUCTOR_MODEL_NAME,
            instruction=settings.EMBEDDING_INSTRUCTION,
            query_instruction=settings.QUERY_INSTRUCTION,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            device=settings.EMBEDDING_DEVICE
        )
    elif embedding_service == "openai":
        service = OpenAIEmbedding(
            model_name=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            batch_size=settings.OPENAI_BATCH_SIZE
        )
    elif embedding_service == "sentence_transformer":
        service = SentenceTransformerEmbedding(
            model_name=settings.SENTENCE_TRANSFORMER_MODEL_NAME,
            batch_size=settings.EMBEDDING_BATCH_SIZE
        )
    else:
        available_services = ["instructor", "openai", "sentence_transformer"]
        logger.error(f"Unsupported embedding service: {embedding_service}")
        raise ValueError(
            f"Unsupported embedding service: {embedding_service}. "
            f"Available options: {', '.join(available_services)}"
        )

    # ✅ Validate dimension immediately
    # TODO ADD if needed
    # await validate_embedding_dimensions(service, expected_dim=settings.EMBEDDING_DIMENSION)
    #
    # # Wrap with caching if enabled
    # if settings.USE_EMBEDDING_CACHE:
    #     logger.info("✅ Enabling embedding cache")
    #     redis_cache = RedisCache(
    #         host=settings.REDIS_HOST,
    #         port=settings.REDIS_PORT,
    #         password=settings.REDIS_PASSWORD,
    #         db=settings.REDIS_DB
    #     )
    #     service = CachedEmbeddingService(
    #         embedding_service=service,
    #         cache_service=redis_cache,
    #         ttl=settings.EMBEDDING_CACHE_TTL
    #     )

    return service