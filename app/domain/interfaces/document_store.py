# core/interfaces/document_store.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.entities.document import Document

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.entities.document import Document


class DocumentStoreInterface(ABC):
    """Interface for document storage services."""

    @abstractmethod
    async def store_document(self, document: Document) -> str:
        pass

    @abstractmethod
    async def get_document(self,document_id: str, owner_id: str, theme_id: str) -> Optional[Document]:
        pass

    @abstractmethod
    async def get_documents(self, document_ids: List[str], owner_id: str, theme_id: str) -> List[Document]:
        pass

    @abstractmethod
    async def update_document(self, document: Document) -> bool:
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        pass

    @abstractmethod
    async def search_documents(self, query: str, limit: int = 5, owner_id: Optional[str] = None) -> List[Document]:
        pass

    @abstractmethod
    async def count_documents(self, filter_criteria: Optional[Dict[str, Any]] = None) -> int:
        pass
