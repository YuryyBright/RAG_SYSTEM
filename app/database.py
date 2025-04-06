from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create PostgreSQL connection URL
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# Create SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """
    Dependency to get a SQLAlchemy DB session.

    Yields
    ------
    Session
        A SQLAlchemy session object.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()