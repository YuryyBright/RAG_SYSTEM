from typing import Dict, List, Optional
import uuid
from core.entities.document import Document

class DocumentStore:
    """
    Simple in-memory document store.

    This class provides methods to save, retrieve, and delete documents in an in-memory store.
    It also maintains a mapping between FAISS index IDs and document IDs.

    Attributes
    ----------
    documents : Dict[str, Document]
        A dictionary mapping document IDs to Document objects.
    faiss_id_map : Dict[int, str]
        A dictionary mapping FAISS index IDs to document IDs.
    next_faiss_id : int
        The next available FAISS index ID.
    """

    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.faiss_id_map: Dict[int, str] = {}  # Maps FAISS index IDs to document IDs
        self.next_faiss_id = 0

    async def save(self, document: Document) -> Document:
        """
        Save a document to the store.

        Parameters
        ----------
        document : Document
            The document to be saved.

        Returns
        -------
        Document
            The saved document with an assigned ID.
        """
        if not document.id:
            document.id = str(uuid.uuid4())

        self.documents[document.id] = document

        # Map FAISS ID to document ID
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
            The document with the specified ID, or None if not found.
        """
        return self.documents.get(document_id)

    async def get_by_faiss_id(self, faiss_id: int) -> Optional[Document]:
        """
        Get a document by its FAISS index ID.

        Parameters
        ----------
        faiss_id : int
            The FAISS index ID of the document to retrieve.

        Returns
        -------
        Optional[Document]
            The document with the specified FAISS index ID, or None if not found.
        """
        doc_id = self.faiss_id_map.get(faiss_id)
        if doc_id:
            return self.documents.get(doc_id)
        return None

    async def get_all(self) -> List[Document]:
        """
        Get all documents.

        Returns
        -------
        List[Document]
            A list of all documents in the store.
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
        if document_id in self.documents:
            del self.documents[document_id]

            # Remove from FAISS ID map
            faiss_id = None
            for fid, did in self.faiss_id_map.items():
                if did == document_id:
                    faiss_id = fid
                    break

            if faiss_id is not None:
                del self.faiss_id_map[faiss_id]

            return True
        return False