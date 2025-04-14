import os
import pickle
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api import Collection
from core.entities.document import Document
from core.interfaces.indexing import IndexInterface


class ChromaVectorIndex(IndexInterface):
    """
    Implementation of a vector index using ChromaDB.

    This class implements the IndexInterface using the ChromaDB client for
    vector similarity search. It stores vectors (embeddings) and their
    associated document metadata.

    Attributes
    ----------
    collection_name : str
        The name of the Chroma collection where documents are stored.
    persistence_path : str
        The file path for local persistence of the Chroma data.
    embedding_dimension : int
        The dimensionality of the vectors (embeddings).
    client : chromadb.Client
        The Chroma client instance.
    collection : chromadb.api.Collection
        The Chroma collection that holds documents and embeddings.
    documents : Dict[str, Document]
        A local cache mapping document IDs to Document objects.
    """

    def __init__(
            self,
            collection_name: str = "documents",
            persistence_path: str = "./data/embeddings/chroma",
            embedding_dimension: int = 1536,  # default dimension for e.g. OpenAI embeddings
    ):
        """
        Initialize the Chroma vector index.

        Parameters
        ----------
        collection_name : str
            The name of the Chroma collection to use.
        persistence_path : str
            The directory where Chroma will store persistent data.
        embedding_dimension : int
            The dimensionality of the vector embeddings.
        """
        self.collection_name = collection_name
        self.persistence_path = persistence_path
        self.embedding_dimension = embedding_dimension

        # Local cache to store Document objects
        self.documents: Dict[str, Document] = {}

        # Create Chroma client
        self.client = chromadb.Client(
            ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persistence_path
            )
        )

        # Create or get existing collection
        self.collection: Collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None  # We'll provide embeddings directly
        )

    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the Chroma collection.

        Parameters
        ----------
        documents : List[Document]
            A list of Document objects to be added to the index.
        """
        docs_with_embeddings = [doc for doc in documents if doc.embedding is not None]
        if not docs_with_embeddings:
            return

        ids = [doc.id for doc in docs_with_embeddings]
        embeddings = [doc.embedding for doc in docs_with_embeddings]
        metadatas = [doc.metadata for doc in docs_with_embeddings]

        # Add to Chroma
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=[doc.content for doc in docs_with_embeddings]
        )

        # Update local cache
        for doc in docs_with_embeddings:
            self.documents[doc.id] = doc

    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the collection for documents similar to the query embedding.

        Parameters
        ----------
        query_embedding : List[float]
            A list of floats representing the embedding of the query.
        k : int, optional
            The number of top similar documents to return (default is 5).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the IDs, content, metadata, and similarity scores
            of the top similar documents.
        """
        if len(self.documents) == 0:
            return []

        # Execute similarity search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # Process results (Chroma returns lists of IDs, metadata, distances, etc.)
        matched_ids = results["ids"][0]
        matched_metadatas = results["metadatas"][0]
        matched_docs = results["documents"][0]
        distances = results["distances"][0]  # By default, this is Euclidean distance

        search_results = []
        for i, doc_id in enumerate(matched_ids):
            # Convert Euclidean distance to a rough similarity (1 - normalized distance)
            dist = float(distances[i])
            score = 1.0 - dist / 2.0

            # Retrieve from local cache if needed
            doc_obj = self.documents.get(doc_id)
            content = matched_docs[i] if doc_obj is None else doc_obj.content

            search_results.append({
                "id": doc_id,
                "content": content,
                "metadata": matched_metadatas[i],
                "score": score
            })

        return search_results

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the Chroma collection and local cache.

        Parameters
        ----------
        doc_id : str
            The unique identifier of the document to be deleted.
        """
        # Remove from Chroma
        self.collection.delete(ids=[doc_id])

        # Remove from cache
        if doc_id in self.documents:
            del self.documents[doc_id]

    async def save_index(self, path: str) -> None:
        """
        Save the current state of the index to disk.

        For Chroma, data is already persisted automatically in the `persistence_path`.
        This method can optionally save the local documents cache to disk.

        Parameters
        ----------
        path : str
            The file path where the document cache should be saved (if desired).
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(f"{path}.chroma_documents", "wb") as f:
            pickle.dump(self.documents, f)

        # The Chroma collection itself is automatically persisted; no further action needed.

    async def load_index(self, path: str) -> None:
        """
        Load the index from disk.

        Chroma data will be loaded automatically when we initialize the client.
        This method can load our local documents cache from disk.

        Parameters
        ----------
        path : str
            The file path from where the document cache should be loaded.
        """
        # Reload the Chroma collection (already done in __init__)
        # Now load the local documents if it exists
        try:
            with open(f"{path}.chroma_documents", "rb") as f:
                self.documents = pickle.load(f)
        except FileNotFoundError:
            self.documents = {}
