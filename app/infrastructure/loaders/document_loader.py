from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid
import json
from datetime import datetime
from api.core.entities.document import Document

class DocumentLoader:
    """
    Load documents from various sources.

    This class provides methods to load documents from a directory, supporting various file formats.

    Attributes
    ----------
    supported_extensions : List[str]
        A list of supported file extensions for loading documents.
    """

    def __init__(self):
        self.supported_extensions = [".txt", ".md", ".json"]

    async def load_from_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Load documents from a directory.

        Parameters
        ----------
        directory_path : str
            Path to the directory.
        recursive : bool, optional
            Whether to recursively search subdirectories (default is True).
        metadata : Optional[Dict[str, Any]], optional
            Additional metadata to attach to all documents (default is None).

        Returns
        -------
        List[Document]
            A list of Document objects loaded from the directory.

        Raises
        ------
        ValueError
            If the directory does not exist.
        """
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Directory {directory_path} does not exist")

        documents = []

        # Determine files to process
        if recursive:
            files = list(path.glob("**/*"))
        else:
            files = list(path.glob("*"))

        # Process each file
        for file_path in files:
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                try:
                    doc = await self._load_file(file_path, metadata)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")

        return documents

    async def _load_file(
        self,
        file_path: Path,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Document]:
        """
        Load a single file.

        Parameters
        ----------
        file_path : Path
            The path to the file to be loaded.
        additional_metadata : Optional[Dict[str, Any]], optional
            Additional metadata to attach to the document (default is None).

        Returns
        -------
        Optional[Document]
            A Document object if the file is successfully loaded, otherwise None.
        """
        # Base metadata
        base_metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "extension": file_path.suffix,
            "created_at": datetime.now().isoformat()
        }

        # Add additional metadata if provided
        if additional_metadata:
            base_metadata.update(additional_metadata)

        # Process based on file type
        if file_path.suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return Document(
                id=str(uuid.uuid4()),
                content=content,
                metadata=base_metadata
            )

        elif file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON formats
            if isinstance(data, dict):
                # If it's a dictionary with "content" field, use that
                content = data.get("content", "")
                # Merge metadata if available
                if "metadata" in data and isinstance(data["metadata"], dict):
                    base_metadata.update(data["metadata"])
            elif isinstance(data, list):
                # If it's a list, join with newlines
                content = "\n".join([str(item) for item in data])
            else:
                # Otherwise convert to string
                content = str(data)

            return Document(
                id=str(uuid.uuid4()),
                content=content,
                metadata=base_metadata
            )

        return None