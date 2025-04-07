# app/models/db_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, LargeBinary, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

def generate_uuid():
    """Generate a unique UUID string."""
    return str(uuid.uuid4())

class User(Base):
    """User model for authentication.

    Attributes
    ----------
    id : str
        Unique identifier for the user.
    username : str
        Unique username for the user.
    email : str
        Unique email address for the user.
    hashed_password : str
        Hashed password for the user.
    is_active : bool
        Indicates if the user is active.
    is_admin : bool
        Indicates if the user has admin privileges.
    created_at : datetime
        Timestamp when the user was created.
    updated_at : datetime
        Timestamp when the user was last updated.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    files = relationship("File", back_populates="owner")
    documents = relationship("Document", back_populates="owner")

class File(Base):
    """File storage model.

    Attributes
    ----------
    id : str
        Unique identifier for the file.
    filename : str
        Name of the file.
    file_path : str
        Path to the file in the file system.
    content_type : str
        MIME type of the file.
    size : int
        Size of the file in bytes.
    is_public : bool
        Indicates if the file is public.
    owner_id : str
        ID of the user who owns the file.
    created_at : datetime
        Timestamp when the file was created.
    updated_at : datetime
        Timestamp when the file was last updated.
    """
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path in file system
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    is_public = Column(Boolean, default=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="files")

class Document(Base):
    """Document model for RAG system.

    Attributes
    ----------
    id : str
        Unique identifier for the document.
    content : str
        Content of the document.
    embedding : bytes
        Embedding of the document stored as binary.
    owner_id : str
        ID of the user who owns the document.
    created_at : datetime
        Timestamp when the document was created.
    updated_at : datetime
        Timestamp when the document was last updated.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    content = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # Store embedding as binary
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="documents")
    document_metadata = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")

class DocumentMetadata(Base):
    """Metadata for Document.

    Attributes
    ----------
    id : str
        Unique identifier for the metadata.
    document_id : str
        ID of the document to which this metadata belongs.
    key : str
        Key of the metadata.
    value : str
        Value of the metadata.
    """
    __tablename__ = "document_metadata"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="document_metadata")

class Token(Base):
    """Token model for authentication.

    Attributes
    ----------
    id : str
        Unique identifier for the token.
    token : str
        The token string.
    user_id : str
        ID of the user to whom the token belongs.
    expires_at : datetime
        Expiration timestamp of the token.
    created_at : datetime
        Timestamp when the token was created.
    """
    __tablename__ = "tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())