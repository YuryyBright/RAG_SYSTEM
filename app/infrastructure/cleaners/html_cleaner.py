# app/infrastructure/cleaners/html_cleaner.py
import re
from .base_cleaner import BaseCleaner


class HtmlCleaner(BaseCleaner):
    """
    Cleaner for HTML text content.

    Handles HTML-specific patterns to extract clean text.
    """

    def clean(self, text: str) -> str:
        """
        Clean HTML text.

        Parameters
        ----------
        text : str
            Text extracted from HTML content.

        Returns
        -------
        str
            Cleaned text with HTML artifacts removed.
        """
        if not text:
            return ""

        # Remove any remaining HTML tags
        text = re.sub(r'<[^>]*>', ' ', text)

        # Convert HTML entities to characters
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'"
        }
        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Clean up any other HTML-specific artifacts
        text = text.replace('\n\n', '\n')

        return text.strip()