# app/config.py
from pydantic import BaseSettings
import os
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RAG API"

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # PostgreSQL settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ragapi")

    # File storage
    FILE_STORAGE_PATH: str = os.getenv("FILE_STORAGE_PATH", "./storage/files")

    # Service URLs
    EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "http://localhost:8001")
    OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
    RERANKER_API_URL: str = os.getenv("RERANKER_API_URL", "http://localhost:8002")

    # RAG Settings
    SCORE_THRESHOLD: float = float(os.getenv("SCORE_THRESHOLD", "0.35"))
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))

    # Model Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "hkunlp/instructor-xl")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Storage
    INDEX_PATH: str = os.getenv("INDEX_PATH", "./data/index")

    class Config:
        case_sensitive = True


# Create global settings object
settings = Settings()