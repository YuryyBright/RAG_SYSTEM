# document_store_interface.py

from core.interfaces.document_store import DocumentStoreInterface
from typing import Dict, List, Optional
import uuid
from core.entities.document import Document

class DocumentStore(DocumentStoreInterface):
    """
    Implementation of the DocumentStoreInterface for managing documents in memory.

    Attributes
    ----------
    documents : Dict[str, Document]
        A dictionary to store documents with their IDs as keys.
    faiss_id_map : Dict[int, str]
        A dictionary to map FAISS index IDs to document IDs.
    next_faiss_id : int
        The next available FAISS index ID.
    """

    def __init__(self):
        """
        Initialize the DocumentStore with empty dictionaries for documents and FAISS ID mapping,
        and set the next FAISS ID to 0.
        """
        self.documents: Dict[str, Document] = {}
        self.faiss_id_map: Dict[int, str] = {}
        self.next_faiss_id = 0

    async def store_document(self, document: Document) -> str:
        """
        Store a document in the document store.

        Parameters
        ----------
        document : Document
            The document to store.

        Returns
        -------
        str
            The ID of the stored document.
        """
        saved_doc = await self.save(document)
        return saved_doc.id

    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document from the document store by its ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to retrieve.

        Returns
        -------
        Optional[Document]
            The retrieved document, or None if not found.
        """
        return await self.get(document_id)

    async def get_documents(self, filter_criteria: Dict = None) -> List[Document]:
        """
        Retrieve multiple documents from the document store based on filter criteria.

        Parameters
        ----------
        filter_criteria : Dict, optional
            Criteria to filter documents (default is None).

        Returns
        -------
        List[Document]
            The retrieved documents.
        """
        return await self.get_all()

    async def update_document(self, document: Document) -> bool:
        """
        Update a document in the document store.

        Parameters
        ----------
        document : Document
            The updated document.

        Returns
        -------
        bool
            True if update was successful, False otherwise.
        """
        if document.id in self.documents:
            self.documents[document.id] = document
            return True
        return False

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the document store by its ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to delete.

        Returns
        -------
        bool
            True if deletion was successful, False otherwise.
        """
        return await self.delete(document_id)

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
        if not document.id:
            document.id = str(uuid.uuid4())

        self.documents[document.id] = document
        self.faiss_id_map[self.next_faiss_id] = document.id
        self.next_faiss_id += 1
        return document

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
        return self.documents.get(document_id)

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
        doc_id = self.faiss_id_map.get(faiss_id)
        return self.documents.get(doc_id) if doc_id else None

    async def get_all(self) -> List[Document]:
        """
        Get all documents.

        Returns
        -------
        List[Document]
            A list of all document entities.
        """
        return list(self.documents.values())

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
        if document_id not in self.documents:
            return False

        del self.documents[document_id]
        faiss_id = next((fid for fid, did in self.faiss_id_map.items() if did == document_id), None)
        if faiss_id is not None:
            del self.faiss_id_map[faiss_id]

        return True