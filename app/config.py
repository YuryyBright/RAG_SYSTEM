"""
Configuration module for the application.

This module loads environment variables and defines settings for the application.
"""

import os
from pydantic import BaseSettings, Field, EmailStr
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    APP_NAME: str = Field("RAG System", description="Application name")
    APP_DESCRIPTION: str = Field("Retrieval-Augmented Generation System", description="Application description")
    APP_VERSION: str = Field("0.1.0", description="Application version")
    ENVIRONMENT: str = Field("development", description="Application environment")
    DEBUG: bool = Field(False, description="Debug mode")

    # Server settings
    HOST: str = Field("0.0.0.0", description="Server host")
    PORT: int = Field(8000, description="Server port")
    CORS_ORIGINS: List[str] = Field(
        ["http://localhost", "http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )

    # Database settings
    DATABASE_URL: str = Field(
        "postgresql+psycopg2://user:password@localhost:5432/dbname",
        description="Database URL"
    )

    # Authentication settings
    SECRET_KEY: str = Field(
        "your-secret-key-placeholder",
        description="Secret key for JWT token"
    )
    ALGORITHM: str = Field("HS256", description="Algorithm for JWT token")
    ACCESS_TOKEN_EXPIRE_DAYS: int = Field(30, description="Access token expiration time in days")

    # AI Model settings
    EMBEDDING_MODEL: str = Field(
        "instructor-xl",
        description="Model name for embedding"
    )
    EMBEDDING_DIMENSION: int = Field(768, description="Dimension of embeddings")
    LLM_MODEL: str = Field(
        "mistral-7b-instruct",
        description="Model name for LLM"
    )
    RERANKER_MODEL: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Model name for reranker"
    )
    SCORE_THRESHOLD: float = Field(0.7, description="Threshold for document relevance score")

    # File storage settings
    UPLOAD_DIR: str = Field("./data/uploads", description="Directory for file uploads")
    MAX_FILE_SIZE: int = Field(10_000_000, description="Maximum file size in bytes")
    ALLOWED_EXTENSIONS: List[str] = Field(
        ["pdf", "txt", "docx", "md", "html", "csv", "json"],
        description="Allowed file extensions"
    )

    # Email settings (optional)
    SMTP_SERVER: Optional[str] = Field(None, description="SMTP server")
    SMTP_PORT: Optional[int] = Field(None, description="SMTP port")
    SMTP_USERNAME: Optional[str] = Field(None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(None, description="SMTP password")
    EMAIL_FROM: Optional[EmailStr] = Field(None, description="Email sender")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()