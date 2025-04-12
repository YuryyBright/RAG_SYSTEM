# app/infrastructure/cache/redis_cache.py
import json
import logging
from typing import Any, Dict, List, Optional, Union
import aioredis
from app.config import settings
from utils.logger_util import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Redis cache implementation for storing and retrieving data.

    This class provides an interface for working with Redis as a cache.
    It handles serialization/deserialization of complex objects and
    provides typed methods for different data structures.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the Redis cache.

        Args:
            redis_url: Redis connection string. If None, uses setting from config.
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.client = None
        self.connected = False

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self.connected:
            try:
                logger.info(f"Connecting to Redis at {self.redis_url}")
                self.client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                self.connected = True
                logger.info("Successfully connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                self.connected = False
                raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.connected and self.client:
            await self.client.close()
            self.connected = False
            logger.info("Disconnected from Redis")

    async def ensure_connected(self) -> None:
        """Ensure connection to Redis is established."""
        if not self.connected:
            await self.connect()

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds

        Returns:
            bool: True if operation succeeded
        """
        await self.ensure_connected()
        try:
            # Handle different data types
            if isinstance(value, (list, dict, bool, int, float, str)) or value is None:
                serialized = json.dumps(value)
            else:
                # Attempt to handle more complex objects
                serialized = json.dumps(value, default=lambda o: o.__dict__)

            if ttl:
                result = await self.client.setex(key, ttl, serialized)
            else:
                result = await self.client.set(key, serialized)

            return result == "OK"
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if key doesn't exist

        Returns:
            Cached value or default
        """
        await self.ensure_connected()
        try:
            value = await self.client.get(key)
            if value is None:
                return default

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return default

    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            bool: True if key was deleted
        """
        await self.ensure_connected()
        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key to check

        Returns:
            bool: True if key exists
        """
        await self.ensure_connected()
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {str(e)}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get the remaining time-to-live for a key.

        Args:
            key: Cache key

        Returns:
            int: TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        await self.ensure_connected()
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return -2

    async def keys(self, pattern: str) -> List[str]:
        """
        Find all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            List of matching keys
        """
        await self.ensure_connected()
        try:
            return await self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys with pattern {pattern}: {str(e)}")
            return []

    async def flush_db(self) -> bool:
        """
        Clear the entire cache database.

        Returns:
            bool: True if operation succeeded
        """
        await self.ensure_connected()
        try:
            return await self.client.flushdb()
        except Exception as e:
            logger.error(f"Error flushing cache database: {str(e)}")
            return False

    # Hash methods for storing dictionaries
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set a hash field."""
        await self.ensure_connected()
        try:
            serialized = json.dumps(value)
            return await self.client.hset(name, key, serialized) >= 0
        except Exception as e:
            logger.error(f"Error setting hash field {name}:{key}: {str(e)}")
            return False

    async def hget(self, name: str, key: str, default: Any = None) -> Any:
        """Get a hash field."""
        await self.ensure_connected()
        try:
            value = await self.client.hget(name, key)
            if value is None:
                return default
            return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting hash field {name}:{key}: {str(e)}")
            return default

    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields in a hash."""
        await self.ensure_connected()
        try:
            result = await self.client.hgetall(name)
            return {k: json.loads(v) for k, v in result.items()}
        except Exception as e:
            logger.error(f"Error getting all hash fields for {name}: {str(e)}")
            return {}

    # List methods
    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to the head of a list."""
        await self.ensure_connected()
        try:
            serialized = [json.dumps(v) for v in values]
            return await self.client.lpush(name, *serialized)
        except Exception as e:
            logger.error(f"Error pushing to list {name}: {str(e)}")
            return 0

    async def rpush(self, name: str, *values: Any) -> int:
        """Push values to the tail of a list."""
        await self.ensure_connected()
        try:
            serialized = [json.dumps(v) for v in values]
            return await self.client.rpush(name, *serialized)
        except Exception as e:
            logger.error(f"Error pushing to list {name}: {str(e)}")
            return 0

    async def lrange(self, name: str, start: int, end: int) -> List[Any]:
        """Get a range of elements from a list."""
        await self.ensure_connected()
        try:
            result = await self.client.lrange(name, start, end)
            return [json.loads(item) for item in result]
        except Exception as e:
            logger.error(f"Error getting range from list {name}: {str(e)}")
            return []

    # Specialized methods for embeddings
    async def store_embedding(self, key: str, embedding: List[float], ttl: Optional[int] = None) -> bool:
        """
        Store an embedding vector.

        Args:
            key: Embedding identifier
            embedding: Vector representation
            ttl: Time-to-live in seconds

        Returns:
            bool: Success status
        """
        cache_key = f"embedding:{key}"
        return await self.set(cache_key, embedding, ttl)

    async def get_embedding(self, key: str) -> Optional[List[float]]:
        """
        Retrieve an embedding vector.

        Args:
            key: Embedding identifier

        Returns:
            List[float]: The embedding vector or None if not found
        """
        cache_key = f"embedding:{key}"
        return await self.get(cache_key)

    async def store_query_results(self, query_hash: str, results: Any, ttl: int = 300) -> bool:
        """
        Store query results.

        Args:
            query_hash: Hash of the query
            results: Query results to cache
            ttl: Time-to-live in seconds

        Returns:
            bool: Success status
        """
        cache_key = f"query_results:{query_hash}"
        return await self.set(cache_key, results, ttl)

    async def get_query_results(self, query_hash: str) -> Optional[Any]:
        """
        Retrieve cached query results.

        Args:
            query_hash: Hash of the query

        Returns:
            Cached query results or None
        """
        cache_key = f"query_results:{query_hash}"
        return await self.get(cache_key)


# Cache singleton factory
_cache_instance = None


async def get_redis_cache() -> RedisCache:
    """
    Get or create a Redis cache instance.

    Returns:
        RedisCache: Singleton Redis cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
        await _cache_instance.connect()
    return _cache_instance