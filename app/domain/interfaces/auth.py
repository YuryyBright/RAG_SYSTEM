# app/core/interfaces/auth.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta

from domain.entities.user import User


class AuthInterface(ABC):
    """Interface for authentication services."""

    @abstractmethod
    async def authenticate_user(self, username: str, password: str, user_provider: Callable) -> Optional[User]:
        pass

    @abstractmethod
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Tuple[
        str, datetime]:
        pass

    @abstractmethod
    async def get_current_user(self, token: str, user_provider: Callable) -> User:
        pass

    @abstractmethod
    async def get_current_active_user(self, token: str, user_provider: Callable) -> User:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        pass
