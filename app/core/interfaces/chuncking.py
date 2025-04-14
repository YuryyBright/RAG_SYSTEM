# app/core/interfaces/chunking.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ChunkingServiceInterface(ABC):
    """Interface for text chunking services."""

    @abstractmethod
    def chunk_text(
            self,
            text: str,
            chunk_size: Optional[int] = None,
            chunk_overlap: Optional[int] = None,
            separator: Optional[str] = None
    ) -> List[str]:
        """
        Split text into overlapping chunks of specified size.

        Parameters:
        -----------
        text : str
            The text to split into chunks
        chunk_size : int, optional
            The maximum size of each chunk (in characters)
        chunk_overlap : int, optional
            The number of characters to overlap between chunks
        separator : str, optional
            The character(s) to use as potential split points

        Returns:
        --------
        List[str]
            List of text chunks
        """
        pass

    @abstractmethod
    def chunk_by_semantic_units(
            self,
            text: str,
            min_chunk_size: int = 500,
            max_chunk_size: int = 1500,
            separator_hierarchy: Optional[List[str]] = None
    ) -> List[str]:
        """
        Split text by semantic units, attempting to keep coherent sections together.

        Parameters:
        -----------
        text : str
            The text to split into chunks
        min_chunk_size : int
            The minimum size of each chunk (in characters)
        max_chunk_size : int
            The maximum size of each chunk (in characters)
        separator_hierarchy : List[str], optional
            Ordered list of separators to use, from highest to lowest priority

        Returns:
        --------
        List[str]
            List of text chunks
        """
        pass