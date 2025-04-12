# utils/security.py
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
from datetime import datetime, timedelta

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from passlib.context import CryptContext

from app.utils.logger_util import get_logger

# Configure logger
logger = get_logger(__name__)

# Password hashing parameters
SALT_LENGTH = 16
HASH_ITERATIONS = 390000  # Recommended by OWASP as of 2024
HASH_ALGORITHM = 'sha256'

# Use passlib for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cookie settings
COOKIE_NAME = "auth_session"
CSRF_COOKIE_NAME = "csrf_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days in seconds


def get_password_hash(password: str) -> str:
    """
    Get the hash of a password using bcrypt.

    Args:
        password (str): The password in plain text.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash using bcrypt.

    Args:
        plain_password (str): The password in plain text.
        hashed_password (str): The hashed password.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_salt() -> bytes:
    """Generate a random salt for password hashing."""
    return os.urandom(SALT_LENGTH)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2 with a random salt.

    Note: This is an alternative to bcrypt, use get_password_hash for most cases.

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


def jwt_encode(
        payload: Dict[str, Any],
        secret_key: str,
        algorithm: str = "HS256",
        expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """
    Encode data into a JWT token.

    Args:
        payload: Data to encode in the token
        secret_key: Secret key for signing
        algorithm: JWT algorithm to use
        expires_delta: Optional expiration time

    Returns:
        Tuple[str, datetime]: JWT token and expiration time
    """
    to_encode = payload.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=1)  # Default to 1 day

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)

    # Handle PyJWT version differences
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')

    return encoded_jwt, expire


def jwt_decode(
        token: str,
        secret_key: str,
        algorithms: list[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token to verify
        secret_key: Secret key used for signing
        algorithms: List of allowed algorithms

    Returns:
        Optional[Dict[str, Any]]: Token payload if valid, None otherwise
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithms)
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


def generate_session_id() -> str:
    """
    Generate a secure random session ID.

    Returns:
        str: Random session ID
    """
    return secure_random_string(32)


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
    except Exception as e:
        logger.warning(f"CSRF token validation failed: {e}")
        return False


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


def create_session_cookie(
        response,
        session_id: str,
        expiry: datetime,
        httponly: bool = True,
        secure: bool = True
) -> None:
    """
    Set a secure session cookie on the response.

    Args:
        response: FastAPI response object
        session_id: Session ID to store
        expiry: Expiration datetime
        httponly: Whether cookie is HttpOnly
        secure: Whether cookie requires HTTPS
    """
    max_age = int((expiry - datetime.utcnow()).total_seconds())
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        max_age=max_age,
        httponly=httponly,  # Prevent JavaScript access
        secure=secure,  # Require HTTPS
        samesite="lax"  # CSRF protection
    )


def set_csrf_cookie(
        response,
        csrf_token: str,
        httponly: bool = True,
        secure: bool = True
) -> None:
    """
    Set a CSRF token cookie on the response.

    Args:
        response: FastAPI response object
        csrf_token: CSRF token to store
        httponly: Whether cookie is HttpOnly (false to allow JS access)
        secure: Whether cookie requires HTTPS
    """
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=3600,  # 1 hour
        httponly=httponly,  # Allow JavaScript access for AJAX
        secure=secure,  # Require HTTPS
        samesite="lax"  # CSRF protection
    )


def clear_auth_cookies(response) -> None:
    """
    Clear authentication cookies from the response.

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(key=COOKIE_NAME)
    response.delete_cookie(key=CSRF_COOKIE_NAME)
