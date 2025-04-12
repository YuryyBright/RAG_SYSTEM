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

    @abstractmethod
    async def save(self, document: Document) -> Document:
        """
        Save a document to the store.

        Parameters
        ----------
        document : Document
            The document entity to save.

        Returns
        -------
        Document
            The saved document entity.
        """
        pass

    @abstractmethod
    async def get(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to retrieve.

        Returns
        -------
        Optional[Document]
            The retrieved document entity or None if not found.
        """
        pass

    @abstractmethod
    async def get_all(self) -> List[Document]:
        """
        Get all documents.

        Returns
        -------
        List[Document]
            A list of all document entities.
        """
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """
        Delete a document by ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to delete.

        Returns
        -------
        bool
            True if the document was deleted, False otherwise.
        """
        pass

    async def get_by_faiss_id(self, faiss_id: int) -> Optional[Document]:
        """
        Get a document by its FAISS index ID.

        Parameters
        ----------
        faiss_id : int
            The FAISS index ID of the document.

        Returns
        -------
        Optional[Document]
            The retrieved document entity or None if not found.
        """
        return None


