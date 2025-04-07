# app/adapters/indexing/faiss_hnsw.py
import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from core.entities.document import Document
from core.interfaces.indexing import IndexInterface


class FaissHNSWIndex(IndexInterface):
    """
    Implementation of FAISS HNSW index for efficient similarity search.

    This class implements the IndexInterface using FAISS HNSW (Hierarchical Navigable
    Small World) algorithm for fast approximate nearest neighbor search.

    Attributes:
        dimension (int): The dimension of the vectors to be indexed.
        ef_construction (int): The size of the dynamic list for HNSW graph construction.
        ef_search (int): The size of the dynamic list for HNSW graph search.
        m (int): The number of bi-directional links created for each new element.
        documents (Dict[str, Document]): A mapping of document IDs to Document objects.
        index (faiss.Index): The FAISS index object.
        id_to_index (Dict[str, int]): A mapping of document IDs to their indices in the index.
        index_to_id (Dict[int, str]): A mapping of indices in the index to document IDs.
    """

    def __init__(
            self,
            dimension: int = 1536,  # Default for OpenAI ada-002
            ef_construction: int = 200,
            ef_search: int = 128,
            m: int = 16
    ):
        """
        Initialize the FAISS HNSW index.

        Args:
            dimension (int): The dimension of the vectors to be indexed.
            ef_construction (int): The size of the dynamic list for HNSW graph construction.
            ef_search (int): The size of the dynamic list for HNSW graph search.
            m (int): The number of bi-directional links created for each new element.
        """
        self.dimension = dimension
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.m = m

        # Initialize the index
        self.documents = {}
        self.index = self._create_index()
        self.id_to_index = {}
        self.index_to_id = {}
        self.current_index = 0

    def _create_index(self) -> faiss.Index:
        """
        Create a new FAISS HNSW index.

        Returns:
            faiss.Index: A newly created FAISS HNSW index.
        """
        # Create the HNSW index
        index = faiss.IndexHNSWFlat(self.dimension, self.m)
        index.hnsw.efConstruction = self.ef_construction
        index.hnsw.efSearch = self.ef_search

        return index

    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the index.

        Args:
            documents (List[Document]): A list of Document objects to be added to the index.
        """
        # Filter out documents without embeddings
        docs_with_embeddings = [doc for doc in documents if doc.embedding is not None]

        if not docs_with_embeddings:
            return

        # Prepare embeddings for indexing
        embeddings = np.array([doc.embedding for doc in docs_with_embeddings], dtype=np.float32)

        # Add embeddings to the index
        self.index.add(embeddings)

        # Update mappings
        for doc in docs_with_embeddings:
            self.documents[doc.id] = doc
            self.id_to_index[doc.id] = self.current_index
            self.index_to_id[self.current_index] = doc.id
            self.current_index += 1

    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index for similar documents to the query embedding.

        Args:
            query_embedding (List[float]): A list of floats representing the embedding of the query.
            k (int): The number of top similar documents to return.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the IDs, content, metadata,
                                 and similarity scores of the top similar documents.
        """
        if self.index.ntotal == 0:
            return []

        # Convert query embedding to numpy array
        query_embedding_np = np.array([query_embedding], dtype=np.float32)

        # Search the index
        distances, indices = self.index.search(query_embedding_np, min(k, self.index.ntotal))

        # Map indices to document IDs and prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            # Convert distance to similarity score (1 - normalized distance)
            score = 1.0 - float(distance) / 2.0  # Assuming L2 distance

            # Get document ID from index
            doc_id = self.index_to_id.get(int(idx))

            if doc_id and doc_id in self.documents:
                doc = self.documents[doc_id]
                results.append({
                    "id": doc_id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": score
                })

        return results

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the index.

        Note: FAISS HNSW does not support direct removal of vectors.
        This implementation removes the document from the mapping dictionaries
        but the vector remains in the index. A full rebuild would be needed
        to completely remove the vector.

        Args:
            doc_id (str): The unique identifier of the document to be deleted.
        """
        if doc_id in self.documents:
            # Remove from documents dictionary
            del self.documents[doc_id]

            # Remove from mappings
            if doc_id in self.id_to_index:
                idx = self.id_to_index[doc_id]
                del self.id_to_index[doc_id]
                if idx in self.index_to_id:
                    del self.index_to_id[idx]

    async def save_index(self, path: str) -> None:
        """
        Save the index to disk.

        Args:
            path (str): The file path where the index should be saved.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save the index
        faiss.write_index(self.index, f"{path}.index")

        # Save the mappings and documents
        with open(f"{path}.mappings", "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "id_to_index": self.id_to_index,
                "index_to_id": self.index_to_id,
                "current_index": self.current_index
            }, f)

    async def load_index(self, path: str) -> None:
        """
        Load the index from disk.

        Args:
            path (str): The file path from where the index should be loaded.
        """
        # Load the index
        self.index = faiss.read_index(f"{path}.index")

        # Load the mappings and documents
        with open(f"{path}.mappings", "rb") as f:
            data = pickle.load(f)
            self.documents = data["documents"]
            self.id_to_index = data["id_to_index"]
            self.index_to_id = data["index_to_id"]
            self.current_index = data["current_index"]