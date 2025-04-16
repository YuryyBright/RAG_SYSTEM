# app/infrastructure/loaders/readers/html_reader.py
from pathlib import Path
from html.parser import HTMLParser

from .base_reader import BaseReader


class HtmlReader(BaseReader):
    """Reader for HTML files."""

    def read(self, path: Path) -> str:
        """
        Extract text content from HTML files.

        Parameters
        ----------
        path : Path
            Path to the HTML file.

        Returns
        -------
        str
            Extracted text content from HTML.
        """
        try:
            # Try to use BeautifulSoup if available for better parsing
            try:
                from bs4 import BeautifulSoup
                content = path.read_text(encoding="utf-8", errors="replace")
                soup = BeautifulSoup(content, "html.parser")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                # Get text
                return soup.get_text(separator=" ", strip=True)
            except ImportError:
                # Fallback to simple HTML parser if BeautifulSoup is not available
                class SimpleHTMLParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.result = []

                    def handle_data(self, d):
                        self.result.append(d)

                parser = SimpleHTMLParser()
                parser.feed(path.read_text(encoding="utf-8", errors="replace"))
                return " ".join(parser.result)
        except Exception as e:
            return f"Error reading HTML: {str(e)}"