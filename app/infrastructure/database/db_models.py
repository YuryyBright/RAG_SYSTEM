# app/models/db_models.py
import json
import uuid
from typing import Any

import user_agents
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, LargeBinary, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.types import JSON
Base = declarative_base()


def generate_uuid():
    """Generate a unique UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """
    User model for authentication and profile information.

    Attributes
    ----------
    id : str
        Unique identifier for the user (UUID).
    username : str
        Unique username.
    email : str
        Unique email address.
    hashed_password : str
        Hashed password for secure authentication.
    is_active : bool
        Flag indicating if the user account is active.
    is_admin : bool
        Flag indicating if the user has administrative privileges.
    avatar_url : str
        URL to the user's avatar image.
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
    avatar_url = Column(String, nullable=True, default="/static/dist/img/user.png")  # <--- ADDED FIELD
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    files = relationship("File", back_populates="owner")
    documents = relationship("Document", back_populates="owner")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("Token", backref="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    # Add this relationship to User class
    themes = relationship("Theme", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("ProcessingTask", back_populates="user", cascade="all, delete-orphan")
class UserActivity(Base):
    """
    Represents a record of user activities in the system.

    Attributes
    ----------
    id : int
        The unique identifier for the activity.
    user_id : int
        The ID of the user who performed the activity.
    activity_type : str
        The type of activity (e.g., login, profile update, etc.).
    description : str
        A detailed description of the activity.
    timestamp : datetime
        The timestamp when the activity occurred.
    user : User
        The user associated with this activity (relationship).
    """
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)  # Primary key for the activity
    user_id = Column(String, ForeignKey("users.id"))  # Foreign key linking to the User table
    activity_type = Column(String(50), nullable=False)  # Type of activity (e.g., login, update)
    description = Column(Text, nullable=False)  # Detailed description of the activity
    timestamp = Column(DateTime, default=func.now())  # Timestamp of the activity

    # Relationships
    user = relationship("User", back_populates="activities")  # Link to the User model

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
    file_path = Column(String, nullable=False, unique=True)  # Path in file system
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    is_public = Column(Boolean, default=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    theme_id = Column(String, ForeignKey("themes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="files")
    themes = relationship("ThemeFile", back_populates="file", cascade="all, delete-orphan")


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
    embedding = Column(Vector(768)) # Store embedding as binary
    file_id = Column(String, ForeignKey("files.id"), nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    theme_id = Column(String, ForeignKey("themes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="documents")
    document_metadata = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan")
    file = relationship("File", backref="documents", lazy="selectin")
    theme = relationship("Theme", back_populates="direct_documents", lazy="selectin")

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


# Add to db_models.py
class Theme(Base):
    """
    Theme model for grouping documents.

    Attributes
    ----------
    id : str
        Unique identifier for the theme (UUID).
    name : str
        Name of the theme.
    description : str
        Description of the theme.
    is_public : bool
        Flag indicating if the theme is publicly accessible.
    owner_id : str
        ID of the user who owns the theme.
    created_at : datetime
        Timestamp when the theme was created.
    updated_at : datetime
        Timestamp when the theme was last updated.
    """
    __tablename__ = "themes"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="themes")
    documents = relationship("ThemeDocument", back_populates="theme", cascade="all, delete-orphan")
    files = relationship("ThemeFile", back_populates="theme", cascade="all, delete-orphan", passive_deletes=True)

    shared_with = relationship("ThemeShare", back_populates="theme", cascade="all, delete-orphan")
    tasks = relationship("ProcessingTask", back_populates="theme", cascade="all, delete-orphan")
    direct_documents = relationship("Document", back_populates="theme", lazy="selectin")


# Junction table for theme-document relationship
class ThemeDocument(Base):
    """
    Junction table linking themes to documents.

    This table establishes a many-to-many relationship between themes and documents,
    allowing a document to belong to multiple themes and a theme to contain multiple documents.

    Attributes
    ----------
    theme_id : str
        The ID of the theme to which the document is linked.
    document_id : str
        The ID of the document linked to the theme.
    added_at : datetime
        The timestamp when the document was added to the theme.
    theme : Theme
        The theme associated with this link (relationship).
    document : Document
        The document associated with this link (relationship).
    """
    __tablename__ = "theme_documents"

    theme_id = Column(String, ForeignKey("themes.id"), primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    theme = relationship("Theme", back_populates="documents")
    document = relationship("Document")


class ThemeFile(Base):
    """
    Junction table linking themes to files.

    This table establishes a many-to-many relationship between themes and files,
    allowing a file to belong to multiple themes and a theme to contain multiple files.

    Attributes
    ----------
    theme_id : str
        The ID of the theme to which the file is linked.
    file_id : str
        The ID of the file linked to the theme.
    added_at : datetime
        The timestamp when the file was added to the theme.
    theme : Theme
        The theme associated with this link (relationship).
    file : File
        The file associated with this link (relationship).
    """
    __tablename__ = "theme_files"

    theme_id = Column(String, ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True)
    file_id = Column(String, ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    theme = relationship("Theme", back_populates="files")
    file = relationship("File", back_populates="themes")


class ThemeShare(Base):
    """
    Table for tracking theme shares between users.

    This table allows themes to be shared between users with specific permissions.

    Attributes
    ----------
    id : str
        Unique identifier for the theme share (UUID).
    theme_id : str
        The ID of the theme being shared.
    shared_by : str
        The ID of the user who shared the theme.
    shared_with : str
        The ID of the user with whom the theme is shared.
    created_at : datetime
        The timestamp when the theme was shared.
    permission : str
        The permission level for the shared theme ("read" or "edit").
    theme : Theme
        The theme associated with this share (relationship).
    owner : User
        The user who shared the theme (relationship).
    recipient : User
        The user with whom the theme is shared (relationship).
    """
    __tablename__ = "theme_shares"

    id = Column(String, primary_key=True, default=generate_uuid)
    theme_id = Column(String, ForeignKey("themes.id"), nullable=False)
    shared_by = Column(String, ForeignKey("users.id"), nullable=False)
    shared_with = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    permission = Column(String, default="read")  # "read" or "edit"

    # Relationships
    theme = relationship("Theme", back_populates="shared_with")
    owner = relationship("User", foreign_keys=[shared_by])
    recipient = relationship("User", foreign_keys=[shared_with])
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
    is_revoked = Column(Boolean, default=False)  # ✅ new column


# Modify in app/infrastructure/database/db_models.py

class ProcessingTask(Base):
    """
    Database model for tracking processing tasks.

    Allows for task persistence across server restarts and user sessions.
    """
    __tablename__ = "processing_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    theme_id = Column(String, ForeignKey("themes.id"), nullable=True)
    task_type = Column(String, nullable=False)  # Using TaskType enum values
    description = Column(String, nullable=True)
    status = Column(String, nullable=False)  # Using TaskStatus enum values
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)  # Serialized JSON list of log entries
    task_metadata = Column(Text, nullable=True)  # Changed from 'metadata' to 'task_metadata'
    steps = Column(Text, nullable=True)  # Serialized JSON array of steps
    current_step = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="tasks")
    theme = relationship("Theme", back_populates="tasks")

    @property
    def logs_list(self):
        """Deserialize logs from JSON string to list."""
        if self.logs:
            return json.loads(self.logs)
        return []

    @logs_list.setter
    def logs_list(self, value):
        """Serialize logs from list to JSON string."""
        self.logs = json.dumps(value)

    @property
    def metadata_dict(self):
        """Deserialize metadata from JSON string to dict."""
        if self.task_metadata:  # Use task_metadata instead of metadata
            return json.loads(self.task_metadata)
        return {}

    @metadata_dict.setter
    def metadata_dict(self, value):
        """Serialize metadata from dict to JSON string."""
        self.task_metadata = json.dumps(value)  # Use task_metadata instead of metadata

    @property
    def steps_list(self):
        """Deserialize steps from JSON string to list."""
        if self.steps:
            return json.loads(self.steps)
        return []

    @steps_list.setter
    def steps_list(self, value):
        """Serialize steps from list to JSON string."""
        self.steps = json.dumps(value)

class Session(Base):
    """
    Database model for user sessions.

    Tracks login sessions, expiration, client info, and CSRF token per session.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    username = Column(String, nullable=False)

    csrf_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    last_accessed = Column(DateTime, nullable=True)

    remember = Column(Boolean, default=False)

    user_agent = Column(String, nullable=True)  # Browser / platform
    ip_address = Column(String, nullable=True)  # Source IP address

    # Relationship
    user = relationship("User", back_populates="sessions")

    @hybrid_property
    def device(self):
        if self.user_agent:
            ua = user_agents.parse(self.user_agent)
            return ua.device.family
        return None

    @hybrid_property
    def browser(self):
        if self.user_agent:
            ua = user_agents.parse(self.user_agent)
            return f"{ua.browser.family} {ua.browser.version_string}"
        return None

    @hybrid_property
    def os(self):
        if self.user_agent:
            ua = user_agents.parse(self.user_agent)
            return f"{ua.os.family} {ua.os.version_string}"
        return None

    @hybrid_property
    def location(self):
        # Placeholder for IP-based geolocation lookup
        # Implement actual geolocation retrieval based on ip_address
        return "Unknown Location"

    @hybrid_property
    def is_current(self):
        # Placeholder logic for determining if the session is the current one
        # Implement actual logic based on application context
        return False


# Adding to app/models/db_models.py

class Conversation(Base):
    """
    Represents a chat conversation session.

    Attributes
    ----------
    id : str
        Unique identifier for the conversation (UUID).
    title : str
        Title or summary of the conversation.
    user_id : str
        ID of the user who owns the conversation.
    created_at : datetime
        Timestamp when the conversation was created.
    updated_at : datetime
        Timestamp when the conversation was last updated.
    is_active : bool
        Flag indicating if the conversation is active.
    theme_id : str
        Optional ID of the knowledge theme associated with this conversation.
    model_id : str
        ID of the AI model used for this conversation.
    conversation_metadata : str
        JSON string containing additional conversation metadata.
    """
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False, default="New Conversation")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    is_active = Column(Boolean, default=True)
    theme_id = Column(String, ForeignKey("themes.id"), nullable=True)
    model_id = Column(String, nullable=True)  # ID of the AI model used
    conversation_metadata = Column("conversation_metadata", JSONB, nullable=True)

    # Relationships
    user = relationship("User", backref="conversations")
    theme = relationship("Theme", backref="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    contexts = relationship("ConversationContext", back_populates="conversation", cascade="all, delete-orphan")

    @property
    def extra_metadata(self) -> dict[str, Any] | None:
        return self.conversation_metadata or {}

    @extra_metadata.setter
    def extra_metadata(self, value: dict[str, Any] | None):
        self.conversation_metadata = value



class Message(Base):
    """
    Represents an individual message in a conversation.

    Attributes
    ----------
    id : str
        Unique identifier for the message (UUID).
    conversation_id : str
        ID of the conversation this message belongs to.
    role : str
        Role of the message sender (user, assistant, system).
    content : str
        Content of the message.
    created_at : datetime
        Timestamp when the message was created.
    tokens : int
        Number of tokens in the message (for quota tracking).
    is_hidden : bool
        Flag indicating if the message should be hidden from UI.
    references : str
        JSON string containing document references used for this message.
    metadata : str
        JSON string containing additional message metadata.
    """
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tokens = Column(Integer, default=0)  # Track token usage
    is_hidden = Column(Boolean, default=False)  # For system messages or internal context
    references = Column(Text, nullable=True)  # JSON string for document references
    message_metadata = Column(Text, nullable=True)  # JSON string for additional metadata

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    @property
    def references_list(self):
        """Deserialize references from JSON string to list."""
        if self.references:
            return json.loads(self.references)
        return []

    @references_list.setter
    def references_list(self, value):
        """Serialize references from list to JSON string."""
        self.references = json.dumps(value)

    @property
    def metadata_dict(self):
        """Deserialize metadata from JSON string to dict."""
        if self.message_metadata:
            return json.loads(self.message_metadata)
        return {}

    @metadata_dict.setter
    def metadata_dict(self, value):
        """Serialize metadata from dict to JSON string."""
        self.message_metadata = json.dumps(value)


class ConversationContext(Base):
    """
    Stores semantic context information for a conversation.

    This model is designed to store embeddings, summaries, or other
    processed information to maintain context over time.

    Attributes
    ----------
    id : str
        Unique identifier for the context entry (UUID).
    conversation_id : str
        ID of the conversation this context belongs to.
    context_type : str
        Type of context (embedding, summary, key_points, etc.).
    content : str
        Textual content of the context.
    embedding : Vector
        Vector embedding of the context for semantic search.
    created_at : datetime
        Timestamp when the context was created.
    updated_at : datetime
        Timestamp when the context was last updated.
    priority : int
        Priority level for this context (higher is more important).
    metadata : str
        JSON string containing additional context metadata.
    """
    __tablename__ = "conversation_contexts"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    context_type = Column(String, nullable=False)  # embedding, summary, key_points, etc.
    content = Column(Text, nullable=True)  # Can be null for pure embedding contexts
    embedding = Column(Vector(768), nullable=True)  # Vector embedding for semantic search
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    priority = Column(Integer, default=1)  # Higher priority contexts are more important
    conversation_metadata = Column(Text, nullable=True)  # JSON string for additional metadata

    # Relationships
    conversation = relationship("Conversation", back_populates="contexts")

    @property
    def metadata_dict(self):
        """Deserialize metadata from JSON string to dict."""
        if self.conversation_metadata:
            return json.loads(self.conversation_metadata)
        return {}

    @metadata_dict.setter
    def metadata_dict(self, value):
        """Serialize metadata from dict to JSON string."""
        self.conversation_metadata = json.dumps(value)