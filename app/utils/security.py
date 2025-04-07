"""
Security utilities for the RAG system including password hashing,
token generation/validation, and other security-related functions.
"""
import os
import base64
import secrets
import hashlib
import hmac
import time
from typing import Optional, Dict, Tuple, Any, Union
import logging
from datetime import datetime, timedelta

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Secret key for token generation (should be loaded from environment variables)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(days=1)  # Default to 1 day

# Password hashing parameters
SALT_LENGTH = 16
HASH_ITERATIONS = 390000  # Recommended by OWASP as of 2024
HASH_ALGORITHM = 'sha256'


def generate_salt() -> bytes:
    """Generate a random salt for password hashing."""
    return os.urandom(SALT_LENGTH)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2 with a random salt.

    Args:
        password: Plain text password
        salt: Optional salt, generated if not provided

    Returns:
        Tuple[bytes, bytes]: (hashed_password, salt)
    """
    if not salt:
        salt = generate_salt()

    password_bytes = password.encode('utf-8')
    hash_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password_bytes,
        salt,
        HASH_ITERATIONS
    )

    return hash_bytes, salt


def verify_password(stored_password: bytes, stored_salt: bytes, provided_password: str) -> bool:
    """
    Verify if a provided password matches the stored hash.

    Args:
        stored_password: Previously hashed password
        stored_salt: Salt used for hashing
        provided_password: Plain text password to verify

    Returns:
        bool: True if passwords match, False otherwise
    """
    hash_to_verify, _ = hash_password(provided_password, stored_salt)
    return hmac.compare_digest(stored_password, hash_to_verify)


def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or JWT_EXPIRATION_DELTA)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Optional[Dict[str, Any]]: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def generate_encryption_key(password: str, salt: bytes) -> bytes:
    """
    Generate an encryption key from a password and salt using PBKDF2.

    Args:
        password: Password to derive key from
        salt: Salt value

    Returns:
        bytes: Encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes for Fernet
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_data(data: Union[str, bytes], key: bytes) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption.

    Args:
        data: Data to encrypt
        key: Encryption key

    Returns:
        bytes: Encrypted data
    """
    fernet = Fernet(key)
    if isinstance(data, str):
        data = data.encode('utf-8')
    return fernet.encrypt(data)


def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using Fernet symmetric encryption.

    Args:
        encrypted_data: Encrypted data
        key: Encryption key

    Returns:
        bytes: Decrypted data
    """
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data)


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        str: API key
    """
    # Generate 32 random bytes (256 bits)
    random_bytes = secrets.token_bytes(32)

    # Convert to a URL-safe base64-encoded string
    api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8')

    # Remove padding '=' characters
    api_key = api_key.rstrip('=')

    return api_key


def secure_random_string(length: int = 16) -> str:
    """
    Generate a secure random string of specified length.

    Args:
        length: Length of the string to generate

    Returns:
        str: Random string
    """
    return secrets.token_hex(length // 2)


def is_valid_csrf_token(token: str, session_token: str) -> bool:
    """
    Validate a CSRF token against the session token.

    Args:
        token: CSRF token to validate
        session_token: Token from the user's session

    Returns:
        bool: True if token is valid, False otherwise
    """
    # Simple time-based validation
    try:
        # Extract timestamp and token parts
        parts = token.split('.')
        if len(parts) != 2:
            return False

        timestamp_str, token_part = parts
        timestamp = int(timestamp_str)

        # Check if token is expired (valid for 1 hour)
        current_time = int(time.time())
        if current_time - timestamp > 3600:  # 1 hour
            return False

        # Verify token
        expected_token = hmac.new(
            session_token.encode(),
            f"{timestamp}".encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(token_part, expected_token)
    except Exception:
        return False


def generate_csrf_token(session_token: str) -> str:
    """
    Generate a CSRF token tied to the session token.

    Args:
        session_token: User's session token

    Returns:
        str: CSRF token
    """
    timestamp = int(time.time())
    token_part = hmac.new(
        session_token.encode(),
        f"{timestamp}".encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return f"{timestamp}.{token_part}"


def sanitize_input(input_string: str) -> str:
    """
    Basic sanitization of user input to prevent injection attacks.
    For more comprehensive protection, use a proper HTML sanitization library.

    Args:
        input_string: String to sanitize

    Returns:
        str: Sanitized string
    """
    # Replace potentially dangerous characters
    replacements = {
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }

    for char, replacement in replacements.items():
        input_string = input_string.replace(char, replacement)

    return input_string