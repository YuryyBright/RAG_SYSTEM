from typing import List, Dict, Any
import os
import pickle
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


class MilvusVectorIndex(IndexInterface):
    """
    Implementation of a Milvus vector database for efficient similarity search.

    This class implements the IndexInterface using Milvus, a vector database designed
    for similarity search and AI applications.

    Attributes
    ----------
    collection_name : str
        The name of the Milvus collection to use.
    dimension : int
        The dimension of the vectors to be indexed.
    host : str
        The host address of the Milvus server.
    port : str
        The port of the Milvus server.
    documents : Dict[str, Document]
        A mapping of document IDs to Document objects.
    collection : Collection
        The Milvus collection object.
    """

    def __init__(
            self,
            collection_name: str = "document_embeddings",
            dimension: int = 1536,  # default dimension for e.g. OpenAI embeddings
            host: str = "localhost",
            port: str = "19530"
    ):
        """
        Initialize the Milvus vector index.

        Parameters
        ----------
        collection_name : str
            The name of the Milvus collection to use.
        dimension : int
            The dimension of the vectors to be indexed.
        host : str
            The host address of the Milvus server.
        port : str
            The port of the Milvus server.
        """
        self.collection_name = collection_name
        self.dimension = dimension
        self.host = host
        self.port = port
        self.documents: Dict[str, Document] = {}
        self.collection: Collection = None

        # Connect to Milvus and create/get the collection
        self._connect_to_milvus()
        self._create_or_get_collection()

    def _connect_to_milvus(self) -> None:
        """Connect to the Milvus server."""
        connections.connect(alias="default", host=self.host, port=self.port)

    def _create_or_get_collection(self) -> None:
        """Create or get an existing collection in Milvus."""
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
            self.collection = Collection(name=self.collection_name, schema=schema)

            # Create an index (example: HNSW)
            index_params = {
                "metric_type": "L2",
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 200}
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)

    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the index.

        Parameters
        ----------
        documents : List[Document]
            A list of Document objects to be added to the index.
        """
        docs_with_embeddings = [doc for doc in documents if doc.embedding is not None]
        if not docs_with_embeddings:
            return

        # Prepare data for insertion
        ids = [doc.id for doc in docs_with_embeddings]
        embeddings = [doc.embedding for doc in docs_with_embeddings]
        metadata = [doc.metadata for doc in docs_with_embeddings]

        # Insert data into the collection
        entities = [ids, embeddings, metadata]
        self.collection.insert(entities)

        # Cache documents
        for doc in docs_with_embeddings:
            self.documents[doc.id] = doc

        # Flush to ensure data is persisted
        self.collection.flush()

    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query embedding.

        Parameters
        ----------
        query_embedding : List[float]
            A list of floats representing the embedding of the query.
        k : int, optional
            The number of top similar documents to return (default is 5).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries containing the IDs, content, metadata, and scores of similar documents.
        """
        # Load collection into memory for searching
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

        search_results = []
        for hits in results:
            for hit in hits:
                doc_id = hit.entity.get("id")
                doc = self.documents.get(doc_id)

                if doc:
                    # Convert L2 distance to a rough similarity
                    score = 1.0 - float(hit.distance) / 2.0
                    search_results.append({
                        "id": doc_id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "score": score
                    })

        # Release collection from memory if desired
        self.collection.release()

        return search_results

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document from the Milvus index.

        Parameters
        ----------
        doc_id : str
            The unique identifier of the document to be deleted.
        """
        expr = f'id == "{doc_id}"'
        self.collection.delete(expr)

        if doc_id in self.documents:
            del self.documents[doc_id]

    async def save_index(self, path: str) -> None:
        """
        Save the index to disk.

        For Milvus, the vector data is already managed/persisted by the Milvus server.
        This method can optionally save the local document cache to disk.

        Parameters
        ----------
        path : str
            The file path where the documents cache will be saved.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(f"{path}.documents", "wb") as f:
            pickle.dump(self.documents, f)

    async def load_index(self, path: str) -> None:
        """
        Load the index from disk.

        For Milvus, the vector data is managed by the server. This method only loads
        the local document cache.

        Parameters
        ----------
        path : str
            The file path from which the documents cache will be loaded.
        """
        try:
            with open(f"{path}.documents", "rb") as f:
                self.documents = pickle.load(f)
        except FileNotFoundError:
            self.documents = {}
