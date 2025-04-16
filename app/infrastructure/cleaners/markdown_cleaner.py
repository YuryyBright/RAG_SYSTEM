# app/infrastructure/cleaners/markdown_cleaner.py
import re
from .base_cleaner import BaseCleaner


class MarkdownCleaner(BaseCleaner):
    """
    Cleaner for Markdown formatted text.

    Handles markdown-specific patterns and converts them to plain text.
    """

    def clean(self, text: str) -> str:
        """
        Clean markdown text.

        Parameters
        ----------
        text : str
            Markdown formatted text.

        Returns
        -------
        str
            Cleaned text with markdown artifacts removed.
        """
        if not text:
            return ""

        # Remove code blocks
        text = re.sub(r'```[^`]*```', ' ', text)

        # Remove inline code
        text = re.sub(r'`[^`]*`', ' ', text)

        # Convert headers to plain text
        text = re.sub(r'#{1,6}\s+(.*?)$', r'\1', text, flags=re.MULTILINE)

        # Convert links to text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Remove HTML tags
        text = re.sub(r'<[^>]*>', ' ', text)

        # Remove special characters used in markdown formatting
        text = re.sub(r'[*_~]', ' ', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text