'''
Configuration module for the application.
'''

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field, EmailStr
from pydantic_settings import BaseSettings

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Ensure logs/ directory exists
log_dir = BASE_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Optional JSON logging
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGING_AVAILABLE = True
except ImportError:
    JSON_LOGGING_AVAILABLE = False

# Logging config
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(log_dir / "app.log"),
            "maxBytes": 10_485_760,  # 10MB
            "backupCount": 10,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "standard",
            "filename": str(log_dir / "error.log"),
            "maxBytes": 10_485_760,
            "backupCount": 10,
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": True,
        },
        "app": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app.api": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

if JSON_LOGGING_AVAILABLE:
    LOGGING_CONFIG["formatters"]["json"] = {
        "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
    }
    LOGGING_CONFIG["handlers"]["console"]["formatter"] = "json"

# Setup logging
from app.infrastructure.logging.logger import LoggerFactory
LoggerFactory.setup_logging(LOGGING_CONFIG)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- App Meta ---
    APP_NAME: str = Field("RAG System", description="Application name")
    APP_DESCRIPTION: str = Field("Retrieval-Augmented Generation System", description="Description")
    APP_VERSION: str = Field("0.1.0", description="Version")
    ENVIRONMENT: str = Field("development", description="Environment")
    DEBUG: bool = Field(False, description="Debug mode")

    # --- Server ---
    HOST: str = Field("0.0.0.0", description="Server host")
    PORT: int = Field(8000, description="Server port")
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost", "http://localhost:3000", "http://localhost:8000"
    ])

    # --- Database ---
    DATABASE_URL: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    PGADMIN_DEFAULT_EMAIL: Optional[str] = None
    PGADMIN_DEFAULT_PASSWORD: Optional[str] = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: Optional[str] = None

    # --- Authentication ---
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # --- Embeddings and Vector DB ---
    VECTOR_DB_TYPE: str = "faiss"
    EMBEDDING_SERVICE: str = "instructor"
    INSTRUCTOR_MODEL_NAME: str = "app/models/instructors/instructor-xl"
    EMBEDDING_INSTRUCTION: str = "Represent the document for retrieval:"
    QUERY_INSTRUCTION: str = "Represent the question for retrieving relevant documents:"
    EMBEDDING_BATCH_SIZE: int = 8
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIMENSION: int = 768

    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BATCH_SIZE: int = 5

    SENTENCE_TRANSFORMER_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # --- Reranker ---
    RERANKER_TYPE: str = "bm25"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_DEFAULT_TOP_K: int = 5
    SCORE_THRESHOLD: float = 0.3

    # --- LLM ---
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Mistral-7B-Instruct-v0.3-Q3_K_L.gguf")
    MODELS_BASE_DIR: str = os.getenv("MODELS_BASE_DIR", str(BASE_DIR / "models/llm"))

    # --- File Storage ---
    DOCUMENT_STORAGE_PATH: Path = Path("./data/processed")
    THEME_STORAGE_PATH: Path = Path("./data/themes")
    UPLOAD_DIR: Path = Path("./data/uploads")
    MAX_FILE_SIZE: int = 10_000_000
    ALLOWED_EXTENSIONS: List[str] = Field(
        ["pdf", "txt", "docx", "md", "html", "csv", "json"],
        description="Allowed file extensions"
    )

    MAX_CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # --- Email SMTP ---
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[EmailStr] = None

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

logging.getLogger("app.config").info(
    f"[+] Loaded settings for: {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]"
)