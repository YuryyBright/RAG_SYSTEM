import os
import numpy as np
import faiss
from typing import List, Dict, Any
from api.core.entities.document import Document
from api.core.interfaces.indexing import IndexInterface
from app.infrastructure.database.document_store import DocumentStore

class FaissHNSWIndex(IndexInterface):
    """
    FAISS implementation of the IndexInterface using HNSW indexing.

    This class provides methods to add, search, delete, save, and load documents in a FAISS HNSW index.

    Attributes
    ----------
    document_store : DocumentStore
        The document store for saving and retrieving documents.
    dimension : int
        The dimensionality of the document embeddings.
    index : faiss.IndexHNSWFlat
        The FAISS HNSW index.
    """

    def __init__(self, document_store: DocumentStore, dimension: int = 768):
        self.document_store = document_store
        self.dimension = dimension
        # HNSW index with L2 distance
        self.index = faiss.IndexHNSWFlat(dimension, 32)  # 32 neighbors per node

    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the index and store.

        Parameters
        ----------
        documents : List[Document]
            A list of Document objects to be added to the index.
        """
        if not documents:
            return

        embeddings = []
        ids = []

        for doc in documents:
            if not doc.embedding:
                raise ValueError(f"Document {doc.id} does not have an embedding")

            # Store document in the document store
            await self.document_store.save(doc)

            # Collect embedding and ID for FAISS index
            embeddings.append(doc.embedding)
            ids.append(doc.id)

        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Add embeddings to FAISS index
        self.index.add(embeddings_array)

    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index for similar documents.

        Parameters
        ----------
        query_embedding : List[float]
            A list of floats representing the embedding of the query.
        k : int, optional
            The number of top similar documents to return (default is 5).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the IDs, content, metadata, and similarity scores of the top similar documents.
        """
        query_array = np.array([query_embedding], dtype=np.float32)

        # Perform the search
        distances, indices = self.index.search(query_array, k)

        # Get document IDs for the results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS returns -1 for not enough results
                continue

            # Get the document from the store
            doc = await self.document_store.get_by_faiss_id(idx)
            if doc:
                results.append({
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity score
                })

        return results

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the index and store.

        Parameters
        ----------
        doc_id : str
            The unique identifier of the document to be deleted.
        """
        # Note: FAISS doesn't support direct deletion
        # To implement deletion, we would need to recreate the index
        # This is a simplified version - in production you'd need a proper deletion strategy
        await self.document_store.delete(doc_id)

    async def save_index(self, path: str) -> None:
        """
        Save the FAISS index to disk.

        Parameters
        ----------
        path : str
            The file path where the index should be saved.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        faiss.write_index(self.index, path)

    async def load_index(self, path: str) -> None:
        """
        Load the FAISS index from disk.

        Parameters
        ----------
        path : str
            The file path from where the index should be loaded.
        """
        if os.path.exists(path):
            self.index = faiss.read_index(path)