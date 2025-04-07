# core/interfaces/document_store.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.entities.document import Document


class DocumentStoreInterface(ABC):
    """
    Interface for document storage services.

    This abstract class defines the methods that any document store
    implementation must provide to work with the system.
    """

    @abstractmethod
    async def store_document(self, document: Document) -> str:
        """
        Store a document in the document store.

        Args:
            document (Document): The document to store.

        Returns:
            str: The ID of the stored document.
        """
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document from the document store.

        Args:
            document_id (str): The ID of the document to retrieve.

        Returns:
            Optional[Document]: The retrieved document, or None if not found.
        """
        pass

    @abstractmethod
    async def get_documents(self, filter_criteria: Dict[str, Any] = None) -> List[Document]:
        """
        Retrieve multiple documents from the document store based on filter criteria.

        Args:
            filter_criteria (Dict[str, Any]): Criteria to filter documents.

        Returns:
            List[Document]: The retrieved documents.
        """
        pass

    @abstractmethod
    async def update_document(self, document: Document) -> bool:
        """
        Update a document in the document store.

        Args:
            document (Document): The updated document.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the document store.

        Args:
            document_id (str): The ID of the document to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        pass