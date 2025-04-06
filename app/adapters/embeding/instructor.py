from typing import List
import httpx
from api.core.entities.document import Document
from api.core.interfaces.embedding import EmbeddingInterface
from app.config import settings


class InstructorEmbedding(EmbeddingInterface):
    """
    Implementation of the EmbeddingInterface using the instructor-xl model.

    This class provides methods to embed documents and queries using a specified model
    through an external API.

    Attributes
    ----------
    model_name : str
        The name of the model to use for embedding.
    api_url : str
        The URL of the embedding API.
    instruction : str
        The instruction to use for embedding documents.
    query_instruction : str
        The instruction to use for embedding queries.
    """

    def __init__(self, model_name: str = "hkunlp/instructor-xl"):
        self.model_name = model_name
        self.api_url = settings.EMBEDDING_API_URL
        self.instruction = "Represent the document for retrieval:"
        self.query_instruction = "Represent the question for retrieving supporting documents:"

    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        Embed a list of documents using the instructor model.

        Parameters
        ----------
        documents : List[Document]
            A list of Document objects to be embedded.

        Returns
        -------
        List[Document]
            The list of Document objects with their embeddings.
        """
        async with httpx.AsyncClient() as client:
            for doc in documents:
                response = await client.post(
                    f"{self.api_url}/embed",
                    json={
                        "model": self.model_name,
                        "instruction": self.instruction,
                        "texts": [doc.content]
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                doc.embedding = data["embeddings"][0]
            return documents

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a query string using the instructor model.

        Parameters
        ----------
        query : str
            The query string to be embedded.

        Returns
        -------
        List[float]
            The embedding of the query as a list of floats.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/embed",
                json={
                    "model": self.model_name,
                    "instruction": self.query_instruction,
                    "texts": [query]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]
