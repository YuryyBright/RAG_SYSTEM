# app/infrastructure/cleaners/cleaner_factory.py
from typing import Dict, Type

from .base_cleaner import BaseCleaner, DefaultTextCleaner # Import the concrete class
from .markdown_cleaner import MarkdownCleaner
from .html_cleaner import HtmlCleaner


class CleanerFactory:
    """
    Factory for creating text cleaners based on file type or content format.
    """

    # Map formats to cleaner classes
    _cleaners: Dict[str, Type[BaseCleaner]] = {
        "markdown": MarkdownCleaner,
        "md": MarkdownCleaner,
        "html": HtmlCleaner,
        "htm": HtmlCleaner
    }

    @classmethod
    def get_cleaner(cls, format_type: str) -> BaseCleaner:
        """
        Get the appropriate cleaner for a content format.

        Parameters
        ----------
        format_type : str
            Content format type or file extension.

        Returns
        -------
        BaseCleaner
            Cleaner instance appropriate for the format.
        """
        format_type = format_type.lower().strip('.')

        cleaner_class = cls._cleaners.get(format_type)
        if cleaner_class:
            return cleaner_class()
        else:
            # Default to plain text with no special cleaning
            return DefaultTextCleaner() # Return the concrete implementation

    @classmethod
    def register_cleaner(cls, format_type: str, cleaner_class: Type[BaseCleaner]) -> None:
        """
        Register a new cleaner for a content format.

        Parameters
        ----------
        format_type : str
            Content format type or file extension (without dot).
        cleaner_class : Type[BaseCleaner]
            Cleaner class to use for this format.
        """
        cls._cleaners[format_type.lower()] = cleaner_class