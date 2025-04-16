import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any
from core.entities.document import Document
from core.interfaces.indexing import IndexInterface


class FaissVectorIndex(IndexInterface):
    """
    Implementation of a FAISS vector index for similarity search.

    This class implements the IndexInterface using a FAISS Flat index (L2 distance).

    Attributes
    ----------
    dimension : int
        The dimension of the vectors to be indexed.
    index : faiss.Index
        The FAISS index object.
    documents : Dict[str, Document]
        A mapping of document IDs to Document objects.
    id_to_index : Dict[str, int]
        A mapping of document IDs to their internal index in FAISS.
    index_to_id : Dict[int, str]
        A reverse mapping from FAISS indices to document IDs.
    current_index : int
        A running counter for assigning indices to documents.
    """

    def __init__(self, dimension: int = 1536):
        """
        Initialize the FAISS index.

        Parameters
        ----------
        dimension : int
            The dimension of the vectors to be indexed (default is 1536).
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents: Dict[str, Document] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.current_index = 0

    async def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the FAISS index.

        Parameters
        ----------
        documents : List[Document]
            A list of Document objects to be added to the index.
        """
        docs_with_embeddings = [doc for doc in documents if doc.embedding is not None]
        if not docs_with_embeddings:
            return

        # Convert to float32 np array
        embeddings = np.array([doc.embedding for doc in docs_with_embeddings], dtype=np.float32)

        # Add to FAISS index
        self.index.add(embeddings)

        # Update local cache and mappings
        for doc in docs_with_embeddings:
            self.documents[doc.id] = doc
            self.id_to_index[doc.id] = self.current_index
            self.index_to_id[self.current_index] = doc.id
            self.current_index += 1

    async def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the FAISS index for similar documents.

        Parameters
        ----------
        query_embedding : List[float]
            A list of floats representing the embedding of the query.
        k : int, optional
            The number of top similar documents to return (default is 5).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dictionaries with document IDs, content, metadata, and similarity scores.
        """
        if self.index.ntotal == 0:
            return []

        # Convert query to float32
        query_np = np.array([query_embedding], dtype=np.float32)

        distances, indices = self.index.search(query_np, min(k, self.index.ntotal))

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            doc_id = self.index_to_id.get(int(idx))
            if doc_id and doc_id in self.documents:
                # Convert L2 distance to a rough similarity
                score = 1.0 - float(dist) / 2.0

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
        Delete a document from the FAISS index.

        NOTE: FAISS IndexFlatL2 does not allow removing individual vectors easily.
        You typically need to rebuild the index. This implementation just removes
        the document from local caches. The actual FAISS data remains.

        Parameters
        ----------
        doc_id : str
            The unique identifier of the document to be deleted.
        """
        if doc_id in self.documents:
            del self.documents[doc_id]

        if doc_id in self.id_to_index:
            idx = self.id_to_index[doc_id]
            del self.id_to_index[doc_id]
            if idx in self.index_to_id:
                del self.index_to_id[idx]

    async def save_index(self, path: str) -> None:
        """
        Save the FAISS index to disk.

        Parameters
        ----------
        path : str
            The file path where the index should be saved.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        faiss.write_index(self.index, f"{path}.index")

        # Save the local mappings
        with open(f"{path}.mappings", "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "id_to_index": self.id_to_index,
                "index_to_id": self.index_to_id,
                "current_index": self.current_index
            }, f)

    async def load_index(self, path: str) -> None:
        """
        Load the FAISS index from disk.

        Parameters
        ----------
        path : str
            The file path from where the index should be loaded.
        """
        self.index = faiss.read_index(f"{path}.index")

        # Load local mappings
        with open(f"{path}.mappings", "rb") as f:
            data = pickle.load(f)
            self.documents = data["documents"]
            self.id_to_index = data["id_to_index"]
            self.index_to_id = data["index_to_id"]
            self.current_index = data["current_index"]

    async def add_vectors(self, vectors: List[List[float]], document_ids: List[str],
                          contents: List[str] = None, metadata: List[Dict] = None) -> None:
        """
        Add vectors directly to the index with associated document information.

        Parameters
        ----------
        vectors : List[List[float]]
            List of embedding vectors to add to the index
        document_ids : List[str]
            List of document IDs corresponding to the vectors
        contents : List[str], optional
            List of document contents
        metadata : List[Dict], optional
            List of metadata dictionaries for each document
        """
        if not vectors or len(vectors) == 0:
            return

        # Convert to float32 np array
        embeddings = np.array(vectors, dtype=np.float32)

        # Add to FAISS index
        self.index.add(embeddings)

        # Create and store Document objects
        for i, (vec, doc_id) in enumerate(zip(vectors, document_ids)):
            content = contents[i] if contents and i < len(contents) else ""
            meta = metadata[i] if metadata and i < len(metadata) else {}

            doc = Document(
                id=doc_id,
                content=content,
                metadata=meta,
                embedding=vec
            )

            self.documents[doc_id] = doc
            self.id_to_index[doc_id] = self.current_index
            self.index_to_id[self.current_index] = doc_id
            self.current_index += 1