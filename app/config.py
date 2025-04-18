"""
Configuration module for the application.

This module loads environment variables and defines settings for the application.
"""

import os
import sys
import logging
from typing import List, Optional
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, EmailStr

# Load environment variables from the root-level .env file
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
# Ensure logs/ directory exists
log_dir = BASE_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Try optional JSON logger
try:
    from pythonjsonlogger import jsonlogger

    json_logging_available = True
except ImportError:
    json_logging_available = False

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(BASE_DIR / "logs/app.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "standard",
            "filename": str(BASE_DIR / "logs/error.log"),
            "maxBytes": 10485760,
            "backupCount": 10
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": True
        },
        "app": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG",
            "propagate": False
        },
        "app.api": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        }
    }
}

# Add JSON formatter if available
if json_logging_available:
    LOGGING_CONFIG["formatters"]["json"] = {
        "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
    }
    # You can set a handler to use it if needed:
    LOGGING_CONFIG["handlers"]["console"]["formatter"] = "json"

# Ensure logs/ directory exists before logging config
log_dir = BASE_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
from app.infrastructure.logging.logger import LoggerFactory

LoggerFactory.setup_logging(LOGGING_CONFIG)


# Settings class
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App meta
    APP_NAME: str = Field("RAG System", description="Application name")
    APP_DESCRIPTION: str = Field("Retrieval-Augmented Generation System", description="Description")
    APP_VERSION: str = Field("0.1.0", description="Version")
    ENVIRONMENT: str = Field("development", description="Environment")
    DEBUG: bool = Field(False, description="Debug mode")

    # Server
    HOST: str = Field("0.0.0.0", description="Server host")
    PORT: int = Field(8000, description="Server port")
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost", "http://localhost:3000", "http://localhost:8000"
    ])

    # Database
    DATABASE_URL:Optional[str] = Field(None, description="PostgreSQL DBURL")
    POSTGRES_DB: Optional[str] = Field(None, description="PostgreSQL DB name (for Docker)")
    POSTGRES_USER: Optional[str] = Field(None, description="PostgreSQL user (for Docker)")
    POSTGRES_PASSWORD: Optional[str] = Field(None, description="PostgreSQL password (for Docker)")
    PGADMIN_DEFAULT_EMAIL: Optional[str] = Field(None, description="pgAdmin email (for Docker)")
    PGADMIN_DEFAULT_PASSWORD: Optional[str] = Field(None, description="pgAdmin password (for Docker)")
    REDIS_URL: Optional[str] = Field(None, description="Redis connection string")
    # PostgreSQL advanced options
    DB_POOL_SIZE: int = Field(10, description="Maximum number of connections in the pool")
    DB_MAX_OVERFLOW: int = Field(20, description="Maximum overflow connections beyond pool size")
    DB_POOL_TIMEOUT: int = Field(30, description="Seconds to wait before giving up on getting a connection")
    DB_POOL_RECYCLE: int = Field(1800, description="Recycle connections after this many seconds")
    DB_ECHO: bool = Field(False, description="Enable SQLAlchemy engine logging")

    # Auth
    SECRET_KEY: str = Field(..., description="JWT Secret")
    ALGORITHM: str = Field("HS256", description="JWT Algorithm")
    JWT_SECRET_KEY: str = Field(..., description="JWT Secret Key")
    ACCESS_TOKEN_EXPIRE_DAYS: int = Field(30, description="Token TTL (days)")

    # AI models
    # File storage additions for document store and themes
    DOCUMENT_STORAGE_PATH: Path = Field(Path("./data/processed"), description="Processed document storage")
    THEME_STORAGE_PATH: Path = Field(Path("./data/themes"), description="Theme storage directory")
    EMBEDDING_CACHE_TTL: int = Field(3600, description="Embedding cache TTL in seconds")
    MAX_CHUNK_SIZE: int = Field(1000, description="Maximum chunk size for document splitting")
    CHUNK_OVERLAP: int = Field(200, description="Overlap between chunks when splitting documents")

    # File storage
    UPLOAD_DIR: Path = Field(Path("./data/uploads"), description="Upload directory")
    MAX_FILE_SIZE: int = Field(10_000_000, description="Max file size in bytes")
    ALLOWED_EXTENSIONS: List[str] = Field(
        ["pdf", "txt", "docx", "md", "html", "csv", "json"],
        description="Allowed extensions"
    )

    # Embedding configuration
    VECTOR_DB_TYPE: str = Field("faiss", description="Type of vector database (e.g., faiss, qdrant, chroma)")

    EMBEDDING_SERVICE: str = Field("instructor",
                                   description="Embedding service to use (instructor, openai, sentence_transformer)")
    INSTRUCTOR_MODEL_NAME: str = Field("hkunlp/instructor-large", description="Instructor model name")
    EMBEDDING_INSTRUCTION: str = Field("Represent the document for retrieval:",
                                       description="Instruction for document embeddings")
    QUERY_INSTRUCTION: str = Field("Represent the question for retrieving relevant documents:",
                                   description="Instruction for query embeddings")
    EMBEDDING_BATCH_SIZE: int = Field(8, description="Number of documents to embed in a batch")
    EMBEDDING_DEVICE: str = Field("cpu", description="Device to run embedding model on (cpu or cuda)")
    EMBEDDING_DIMENSION: int = Field(1536, description="Dimension of embedding vectors")
    OPENAI_EMBEDDING_MODEL: str = Field("text-embedding-3-small", description="OpenAI embedding model")
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    OPENAI_BATCH_SIZE: int = Field(5, description="Batch size for OpenAI API calls")
    SENTENCE_TRANSFORMER_MODEL_NAME: str = Field("all-MiniLM-L6-v2", description="SentenceTransformer model name")

    # LLM and Reranker configuration
    LLM_MODEL: str = Field("mistral/mistral-7b-instruct-v0.2", description="LLM model name")
    RERANKER_MODEL: str = Field("cross-encoder/ms-marco-MiniLM-L-6-v2", description="Cross-encoder model for reranking")
    SCORE_THRESHOLD: float = Field(0.3, description="Minimum similarity score for retrieval")
    # Email
    SMTP_SERVER: Optional[str] = Field(None, description="SMTP server")
    SMTP_PORT: Optional[int] = Field(None, description="SMTP port")
    SMTP_USERNAME: Optional[str] = Field(None, description="SMTP user")
    SMTP_PASSWORD: Optional[str] = Field(None, description="SMTP password")
    EMAIL_FROM: Optional[EmailStr] = Field(None, description="Sender email")

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True
        extra = "allow"


# Initialize settings with error handling
try:
    settings = Settings()
except Exception as e:
    logging.exception(f"[-] Failed to load settings. Check your .env configuration. {e}")
    sys.exit(1)

# Log some helpful startup info
logging.getLogger("app.config").info(
    f"[+] Loaded settings for: {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
