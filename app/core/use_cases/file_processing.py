# app/core/use_cases/file_processing.py
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from core.entities.document import Document
from infrastructure.loaders.file_processor import FileProcessor


class FileProcessingUseCase:
    """
    Use case for processing files with improved language detection and reporting.

    This use case leverages the EnhancedFileProcessor to read different types of files,
    detect languages, and prepare text for vector database storage in a RAG system.
    """

    def __init__(self, file_processor: Optional[FileProcessor] = None):
        """
        Initialize the use case with a file processor.

        Parameters
        ----------
        file_processor : EnhancedFileProcessor, optional
            The file processor to use. If not provided, a new one will be created.
        """
        self.file_processor = file_processor or FileProcessor()

    async def process_directory(
            self,
            directory_path: str,
            recursive: bool = True,
            metadata: Dict[str, Any] = None
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """
        Process all files in a directory for the RAG system.

        Parameters
        ----------
        directory_path : str
            Path to the directory containing files to process.
        recursive : bool, optional
            Whether to process subdirectories (default is True).
        metadata : Dict[str, Any], optional
            Additional metadata to attach to all documents.

        Returns
        -------
        Tuple[List[Document], Dict[str, Any]]
            - List of processed documents ready for vector database
            - Processing report with details on successful, unreadable, and warning files
        """
        return await self.file_processor.process_directory(
            directory_path, recursive, metadata
        )

    async def analyze_document_quality(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Analyze the quality of processed documents.

        Parameters
        ----------
        documents : List[Document]
            List of documents to analyze.

        Returns
        -------
        Dict[str, Any]
            Analysis results with quality metrics.
        """
        results = {
            "total_documents": len(documents),
            "empty_documents": 0,
            "short_documents": 0,
            "documents_by_language": {},
            "average_document_length": 0
        }

        total_length = 0

        for doc in documents:
            content_length = len(doc.content)
            total_length += content_length

            # Count empty documents
            if content_length == 0:
                results["empty_documents"] += 1

            # Count short documents (less than 50 characters)
            elif content_length < 50:
                results["short_documents"] += 1

            # Track document language distribution
            language = doc.metadata.get("language", "unknown")
            if language in results["documents_by_language"]:
                results["documents_by_language"][language] += 1
            else:
                results["documents_by_language"][language] = 1

        # Calculate average document length
        if documents:
            results["average_document_length"] = total_length / len(documents)

        return results