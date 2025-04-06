from typing import List, Optional, Dict, Any
import numpy as np
import pickle

from fastapi import Depends
from sqlalchemy.orm import Session
from api.core.entities.document import Document as DocumentEntity
from app.models.db_models import Document as DocumentModel, DocumentMetadata
from app.database import get_db


class PostgresDocumentStore:
    """
    PostgreSQL implementation of document store.

    Parameters
    ----------
    db : Session
        SQLAlchemy session for database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    async def save(self, document: DocumentEntity) -> DocumentEntity:
        """
        Save a document to the store.

        Parameters
        ----------
        document : DocumentEntity
            The document entity to save.

        Returns
        -------
        DocumentEntity
            The saved document entity.
        """
        embedding_binary = pickle.dumps(document.embedding) if document.embedding else None

        db_document = DocumentModel(
            id=document.id,
            content=document.content,
            embedding=embedding_binary,
            owner_id=document.metadata.get("owner_id", "system")
        )
        self.db.add(db_document)

        for key, value in document.metadata.items():
            if key != "owner_id":
                metadata = DocumentMetadata(
                    document_id=document.id,
                    key=key,
                    value=str(value)
                )
                self.db.add(metadata)

        self.db.commit()
        self.db.refresh(db_document)

        return self._db_to_entity(db_document)

    async def get(self, document_id: str) -> Optional[DocumentEntity]:
        """
        Get a document by ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to retrieve.

        Returns
        -------
        Optional[DocumentEntity]
            The retrieved document entity or None if not found.
        """
        db_document = self.db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not db_document:
            return None

        return self._db_to_entity(db_document)

    async def get_by_faiss_id(self, faiss_id: int) -> Optional[DocumentEntity]:
        """
        Get a document by its FAISS index ID.

        Parameters
        ----------
        faiss_id : int
            The FAISS index ID of the document.

        Returns
        -------
        Optional[DocumentEntity]
            The retrieved document entity or None if not found.
        """
        return None

    async def get_all(self) -> List[DocumentEntity]:
        """
        Get all documents.

        Returns
        -------
        List[DocumentEntity]
            A list of all document entities.
        """
        db_documents = self.db.query(DocumentModel).all()
        return [self._db_to_entity(doc) for doc in db_documents]

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
        db_document = self.db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not db_document:
            return False

        self.db.delete(db_document)
        self.db.commit()
        return True

    def _db_to_entity(self, db_document: DocumentModel) -> DocumentEntity:
        """
        Convert DB model to entity.

        Parameters
        ----------
        db_document : DocumentModel
            The database model of the document.

        Returns
        -------
        DocumentEntity
            The document entity.
        """
        metadata = {meta.key: meta.value for meta in db_document.metadata}
        metadata["owner_id"] = db_document.owner_id

        embedding = pickle.loads(db_document.embedding) if db_document.embedding else None

        return DocumentEntity(
            id=db_document.id,
            content=db_document.content,
            metadata=metadata,
            embedding=embedding,
            created_at=db_document.created_at,
            updated_at=db_document.updated_at
        )


def get_document_store(db: Session = Depends(get_db)) -> PostgresDocumentStore:
    """
    Factory function for dependency injection.

    Parameters
    ----------
    db : Session
        SQLAlchemy session for database operations.

    Returns
    -------
    PostgresDocumentStore
        An instance of PostgresDocumentStore.
    """
    return PostgresDocumentStore(db)