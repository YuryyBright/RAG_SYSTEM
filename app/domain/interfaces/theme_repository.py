# app/core/interfaces/theme_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ThemeRepositoryInterface(ABC):
    """
    Interface for theme repository operations.

    Defines the required methods for interacting with the theme persistence layer.
    """

    @abstractmethod
    async def create_theme(self, name: str, description: Optional[str], is_public: bool, owner_id: str) -> str:
        pass

    @abstractmethod
    async def get_theme(self, theme_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def get_themes(self, owner_id: Optional[str] = None, include_public: bool = False) -> List[Any]:
        pass

    @abstractmethod
    async def update_theme(self, theme_id: str, updates: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def delete_theme(self, theme_id: str) -> bool:
        pass

    @abstractmethod
    async def add_document_to_theme(self, theme_id: str, document_id: str) -> bool:
        pass

    @abstractmethod
    async def remove_document_from_theme(self, theme_id: str, document_id: str) -> bool:
        pass

    @abstractmethod
    async def get_theme_documents(self, theme_id: str) -> List[str]:
        pass

    @abstractmethod
    async def count_documents(self, theme_id: str) -> int:
        pass

    @abstractmethod
    async def add_file_to_theme(self, theme_id: str, file_id: str) -> bool:
        pass

    @abstractmethod
    async def remove_file_from_theme(self, theme_id: str, file_id: str) -> bool:
        pass

    @abstractmethod
    async def get_theme_files(self, theme_id: str) -> List[Any]:
        pass