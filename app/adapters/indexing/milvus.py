# app/adapters/indexing/milvus.py
from typing import List, Dict, Any, Optional
import os
import numpy as np
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)
from core.entities.document import Document
from core.interfaces.indexing import IndexInterface


class MilvusIndex(IndexInterface):
    """
    Implementation of Milvus vector database for efficient similarity search.

    This class implements the IndexInterface using Milvus, a vector database designed
    for similarity search and AI applications.

    Attributes:
        collection_name (str): The name of the Milvus collection to use.
        dimension (int): The dimension of the vectors to be indexed.
        host (str): The host address of the Milvus server.
        port (str): The port of the Milvus server.
        documents (Dict[str, Document]): A mapping of document IDs to Document objects.
        collection (Collection): The Milvus collection object.
    """

    def __init__(
            self,
            collection_name: str = "document_embeddings",
            dimension: int = 1536,  # Default for OpenAI ada-002
            host: str = "localhost",
            port: str = "19530"
    ):
        """
        Initialize the Milvus index.

        Args:
            collection_name (str): The name of the Milvus collection to use.
            dimension (int): The dimension of the vectors to be indexed.
            host (str): The host address of the Milvus server.
            port (str): The port of the Milvus server.
        """
        self.collection_name = collection_name
        self.dimension = dimension
        self.host = host
        self.port = port
        self.documents = {}
        self.collection = None

        # Connect to Milvus
        self._connect_to_milvus()

        # Create or get collection
        self._create_or_get_collection()

    def _connect_to_milvus(self) -> None:
        """
        Connect to the Milvus server.
        """
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port
        )

    def _create_or_get_collection(self) -> None:
        """
        Create a new collection in Milvus or get an existing one.
        """
        if utility.has_collection(self.collection_name):
            self.collection = Collection(name=self.collection_name)
        else:
            # Define fields for the collection
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]

            # Create collection schema
            schema = CollectionSchema(fields=fields)

            # Create collection
            self.collection = Collection(name=self.collection_name, schema=schema)

            # Create index
            index_params = {
                "metric_type": "L2",
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 200}
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)

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

        # Prepare data for insertion
        ids = [doc.id for doc in docs_with_embeddings]
        embeddings = [doc.embedding for doc in docs_with_embeddings]
        metadata = [doc.metadata for doc in docs_with_embeddings]

        # Insert data into collection
        entities = [ids, embeddings, metadata]
        self.collection.insert(entities)

        # Cache documents
        for doc in docs_with_embeddings:
            self.documents[doc.id] = doc

        # Flush to ensure data is visible for search
        self.collection.flush()

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
        # Load collection
        self.collection.load()

        # Search parameters
        search_params = {"metric_type": "L2", "params": {"ef": 128}}

        # Execute search
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["id", "metadata"]
        )

        # Process results
        search_results = []
        for hits in results:
            for hit in hits:
                doc_id = hit.entity.get('id')

                # Get document from cache or fetch from storage
                doc = self.documents.get(doc_id)

                if doc:
                    # Convert distance to similarity score (1 - normalized distance)
                    score = 1.0 - float(hit.distance) / 2.0  # Assuming L2 distance

                    search_results.append({
                        "id": doc_id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "score": score
                    })

        # Release collection
        self.collection.release()

        return search_results

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the index.

        Args:
            doc_id (str): The unique identifier of the document to be deleted.
        """
        # Delete from Milvus
        expr = f'id == "{doc_id}"'
        self.collection.delete(expr)

        # Remove from cache
        if doc_id in self.documents:
            del self.documents[doc_id]

    async def save_index(self, path: str) -> None:
        """
        Save the index to disk.

        For Milvus, the data is already persisted in the Milvus server.
        This method only saves the document cache.

        Args:
            path (str): The file path where the document cache should be saved.
        """
        import pickle
        import os

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Save document cache
        with open(f"{path}.documents", "wb") as f:
            pickle.dump(self.documents, f)

    async def load_index(self, path: str) -> None:
        """
        Load the index from disk.

        For Milvus, this method only loads the document cache.

        Args:
            path (str): The file path from where the document cache should be loaded.
        """
        import pickle

        # Load document cache if file exists
        try:
            with open(f"{path}.documents", "rb") as f:
                self.documents = pickle.load(f)
        except FileNotFoundError:
            self.documents = {}