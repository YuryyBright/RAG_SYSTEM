# app/infrastructure/loaders/readers/json_reader.py
import json
from pathlib import Path

from .base_reader import BaseReader


class JsonReader(BaseReader):
    """Reader for JSON files."""

    def read(self, path: Path) -> str:
        """
        Read and extract text from JSON files.

        Parameters
        ----------
        path : Path
            Path to the JSON file.

        Returns
        -------
        str
            Extracted text content from JSON.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

                if isinstance(data, dict):
                    # Try to extract content field or stringify the dict
                    return data.get("content", json.dumps(data, ensure_ascii=False))
                elif isinstance(data, list):
                    # Stringify each item in the list
                    return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
                return str(data)
        except json.JSONDecodeError as e:
            return f"Invalid JSON file: {str(e)}"
        except Exception as e:
            return f"Error reading JSON file: {str(e)}"