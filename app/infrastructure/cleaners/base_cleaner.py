# app/infrastructure/cleaners/base_cleaner.py
from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    """
    Abstract base class for text cleaners.

    Text cleaners process raw text extracted from documents to improve quality
    for RAG systems by removing irrelevant content, normalizing formatting, etc.
    """

    @abstractmethod
    def clean(self, text: str) -> str:
        """
        Clean and normalize text content.

        Parameters
        ----------
        text : str
            Raw text to clean.

        Returns
        -------
        str
            Cleaned and normalized text.
        """
        pass