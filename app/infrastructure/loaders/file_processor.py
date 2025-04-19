# app/infrastructure/loaders/file_processor.py
import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities.document import Document
from core.entities.processed_file import ProcessedFile
from infrastructure.database.repository.file_repository import FileRepository
from utils.logger_util import get_logger
from .readers.reader_factory import ReaderFactory
from .readers.base_reader import BaseReader
from infrastructure.cleaners.cleaner_factory import CleanerFactory
from infrastructure.cleaners.base_cleaner import BaseCleaner  # Import BaseCleaner

logger = get_logger(__name__)


class FileProcessor:
    """
    File processor for reading various file types, detecting language,
    and preparing text for vector database storage in a RAG system.

    Provides detailed reporting on processed files, including warnings for
    unreadable files and language detection failures.
    """

    def __init__(self, file_repository: FileRepository):
        self.supported_extensions = {
            "txt", "md", "markdown", "html", "htm", "pdf", "doc", "docx",
            "csv", "xls", "xlsx", "json", "xml", "ppt", "pptx", "rtf", "yaml", "yml"
        }
        self.successful_files = []
        self.unreadable_files = []
        self.language_detection_failures = []
        self.files_with_warnings = []
        self.file_repository = file_repository

    async def process_directory(
            self,
            directory_path: str,
            recursive: bool = True,
            metadata: Optional[Dict[str, Any]] = None
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
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Directory {directory_path} does not exist or is not a directory")

        # Clear previous processing results
        self.successful_files.clear()
        self.unreadable_files.clear()
        self.language_detection_failures.clear()
        self.files_with_warnings.clear()

        # Get all files or files in all subdirectories if recursive
        files = path.rglob("*") if recursive else path.glob("*")

        documents = []
        for file_path in files:
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()

            # Skip files with unsupported extensions
            if suffix.lstrip('.') not in self.supported_extensions:
                logger.info(f"Skipping unsupported file type: {file_path}")
                continue

            try:
                processed_file = await self.process_file(file_path, metadata)

                # Handle the processed file based on its status
                if processed_file.is_readable:
                    doc = await self._convert_to_document(processed_file, file_path)
                    if doc:  # Only add valid documents
                        documents.append(doc)
                    has_warnings = False

                    # Check for language detection failures
                    if not processed_file.is_language_detected:
                        self.language_detection_failures.append(processed_file)
                        has_warnings = True

                    # Check for other warnings in metadata
                    if processed_file.metadata.get("has_warnings", False):
                        has_warnings = True

                    if has_warnings:
                        self.files_with_warnings.append(processed_file)
                    else:
                        self.successful_files.append(processed_file)
                else:
                    self.unreadable_files.append(processed_file)
                logger.info(f"Finished processing file {file_path}")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                # Create a processed file record for the failure
                failed_file = ProcessedFile(
                    id=str(uuid.uuid4()),
                    filename=file_path.name,
                    content="",
                    is_readable=False,
                    metadata={
                        "source": str(file_path),
                        "error": str(e),
                        "file_size": file_path.stat().st_size if file_path.exists() else 0
                    }
                )
                self.unreadable_files.append(failed_file)

        # Generate the report
        report = self._generate_enhanced_report()
        return documents, report

    async def process_file(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ProcessedFile:
        """
        Process a single file: read content and detect language.

        Parameters
        ----------
        file_path : Path
            Path to the file to process.
        metadata : Dict[str, Any], optional
            Additional metadata to attach to the processed file.

        Returns
        -------
        ProcessedFile
            Processed file entity with content and metadata.
        """
        # Create base metadata
        meta = {
            "source": str(file_path),
            "filename": file_path.name,
            "extension": file_path.suffix,
            "file_size": file_path.stat().st_size,
            "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "processed_at": datetime.now().isoformat(),
            "has_warnings": False
        }

        # Add user-provided metadata
        if metadata:
            meta.update(metadata)

        content = ""
        is_readable = True

        try:
            # Get appropriate reader for this file
            reader = ReaderFactory.get_reader(file_path)
            content = reader.read(file_path)

            # If needed, apply content-specific cleaner
            extension = file_path.suffix.lower().lstrip('.')
            cleaner = CleanerFactory.get_cleaner(extension)
            content = cleaner.clean(content)

        except ValueError as e:
            is_readable = False
            meta["error"] = f"No reader available: {str(e)}"
            meta["has_warnings"] = True
        except Exception as e:
            is_readable = False
            meta["error"] = str(e)
            meta["has_warnings"] = True
            logger.warning(f"Could not read file {file_path}: {e}")

        # Detect language if content is readable
        language = None
        is_language_detected = False

        if is_readable and content.strip():
            try:
                # Only attempt language detection if content is substantial
                if len(content.strip()) > 20:  # Increased minimum content length for better detection
                    language = detect(content[:5000])  # Use only first part for efficiency
                    is_language_detected = True
                else:
                    meta["language_error"] = "Content too short for reliable language detection"
                    meta["has_warnings"] = True
            except LangDetectException as e:
                meta["language_error"] = f"Language detection failed: {str(e)}"
                meta["has_warnings"] = True
            except Exception as e:
                meta["language_error"] = f"Error during language detection: {str(e)}"
                meta["has_warnings"] = True

        # Create processed file entity
        return ProcessedFile(
            id=str(uuid.uuid4()),
            filename=file_path.name,
            content=content,
            language=language,
            is_readable=is_readable,
            is_language_detected=is_language_detected,
            metadata=meta
        )

    async def _convert_to_document(self, pf: ProcessedFile, file_path: Path) -> Optional[Document]:
        """
        Convert a ProcessedFile to a Document for vector database storage.

        Parameters
        ----------
        pf : ProcessedFile
            Processed file to convert
        file_path : Path
            Path to the original file

        Returns
        -------
        Optional[Document]
            Document object or None if conversion fails
        """
        # Copy metadata to avoid modifying the original
        meta = pf.metadata.copy() if pf.metadata else {}

        # Add language info to metadata
        if pf.language:
            meta["language"] = pf.language

        # Add warning flags
        if not pf.is_language_detected:
            meta["language_detection_failed"] = True

        # Fetch file from DB using path
        try:
            file_record = await self.file_repository.get_file_by_path(str(file_path))
            if file_record:
                return Document(
                    id=pf.id,
                    content=pf.content,
                    metadata=meta,
                    file_id=file_record.id,
                    owner_id=file_record.owner_id,
                    theme_id=file_record.theme_id
                )
            logger.warning(f"File not found in database: {str(file_path)}")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch file from DB for path {meta.get('source')}: {e}")
            return None

    def _generate_enhanced_report(self) -> Dict[str, Any]:
        """
        Generate a detailed report of file processing results.

        Returns
        -------
        Dict[str, Any]
            Processing report with summary, details, and recommendations.
        """
        # Extract data for the report
        successful = [asdict(f) for f in self.successful_files]
        unreadable = [asdict(f) for f in self.unreadable_files]
        language_failures = [asdict(f) for f in self.language_detection_failures]
        warnings = [asdict(f) for f in self.files_with_warnings]

        # Files that might need manual review
        files_to_review = []
        for file in self.files_with_warnings:
            files_to_review.append(file.filename)

        # Files that might need to be removed
        files_to_consider_removing = []
        for file in self.unreadable_files:
            files_to_consider_removing.append(file.filename)

        # For empty files with no errors, suggest removal
        for file in self.successful_files:
            if not file.content.strip() and file.is_readable:
                files_to_consider_removing.append(file.filename)

        return {
            "summary": {
                "total_files": len(successful) + len(unreadable) + len(warnings),
                "successful": len(successful),
                "unreadable": len(unreadable),
                "language_detection_failures": len(language_failures),
                "files_with_warnings": len(warnings)
            },
            "details": {
                "successful_files": [{"filename": f["filename"], "language": f["language"]} for f in successful],
                "unreadable_files": [{"filename": f["filename"], "error": f["metadata"].get("error")} for f in
                                     unreadable],
                "language_detection_failures": [
                    {"filename": f["filename"], "error": f["metadata"].get("language_error")} for f in
                    language_failures],
                "files_with_warnings": [{"filename": f["filename"], "warnings": self._extract_warnings(f["metadata"])}
                                        for f in warnings]
            },
            "recommendations": {
                "files_to_review": files_to_review,
                "files_to_consider_removing": files_to_consider_removing
            }
        }

    def _extract_warnings(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Extract warning messages from file metadata.

        Parameters
        ----------
        metadata : Dict[str, Any]
            File metadata containing warning information.

        Returns
        -------
        List[str]
            List of warning messages.
        """
        warnings = []

        if not metadata:
            return warnings

        if "language_error" in metadata:
            warnings.append(f"Language detection issue: {metadata['language_error']}")

        if "error" in metadata:
            warnings.append(f"Processing error: {metadata['error']}")

        return warnings
