# app/core/interfaces/chunking.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from abc import ABC, abstractmethod
from typing import List, Optional


class ChunkingServiceInterface(ABC):
    """Interface for text chunking services."""

    @abstractmethod
    def chunk_text(self, text: str, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None,
                   separator: Optional[str] = None) -> List[str]:
        pass

    @abstractmethod
    def chunk_by_semantic_units(self, text: str, min_chunk_size: int = 500, max_chunk_size: int = 1500,
                                separator_hierarchy: Optional[List[str]] = None) -> List[str]:
        pass
