# app/core/use_cases/file_processing.py
import os
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

from adapters.storage.document_store import DocumentStore
from app.core.entities.document import Document
from app.adapters.storage.file_manager import FileManager
from core.services.embedding_service import EmbeddingService
from core.services.vector_index_services import VectorIndex
from utils.logger_util import get_logger

loggrer = get_logger(__name__)


class FileProcessor:
    """Handles the processing of different file types into text documents."""

    def __init__(self):
        self.supported_extensions = [
            "pdf", "txt", "docx", "doc", "html", "htm", "md", "markdown",
            "csv", "json", "xml", "pptx", "xlsx", "xls", "rtf", "odt"
        ]

    async def process_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Process a file and return its text content and metadata."""
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        file_extension = os.path.splitext(file_path)[1].lower().replace(".", "")

        if file_extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Determine appropriate loader based on file extension
        content, metadata = await self._load_file_content(file_path, file_extension)

        # Add file metadata
        file_stat = os.stat(file_path)
        metadata.update({
            "source": file_path,
            "file_type": file_extension,
            "file_size": file_stat.st_size,
            "last_modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
        })

        return content, metadata

    async def _load_file_content(self, file_path: str, file_extension: str) -> Tuple[str, Dict[str, Any]]:
        """Load content from a file based on its extension."""
        # This would use different loaders from your infrastructure
        # For now, we'll use a simple text loader for demonstration
        if file_extension in ["txt", "md", "markdown"]:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            return content, {"mime_type": "text/plain"}

        # For PDF, DOCX, etc. we would use specialized loaders
        # In a real implementation, you would import and use them:
        # e.g., from app.infrastructure.loaders.pdf_loader import PDFLoader

        # For now, we'll simulate successful loading
        with open(file_path, "rb") as file:
            # Just read the first 1000 bytes to check if file is readable
            file.read(1000)

        return f"Simulated content for {file_path}", {"mime_type": f"application/{file_extension}"}


class FileProcessingUseCase:
    """Use case for processing files for the RAG system."""

    def __init__(
            self,
            file_processor: FileProcessor,
            embedding_service: EmbeddingService,
            document_store: DocumentStore,
            vector_index: VectorIndex,
            file_manager: FileManager
    ):
        self.file_processor = file_processor
        self.embedding_service = embedding_service
        self.document_store = document_store
        self.vector_index = vector_index
        self.file_manager = file_manager

    async def process_directory(
            self,
            directory_path: str,
            recursive: bool = True,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """
        Process all files in a directory, converting them to documents.

        Args:
            directory_path: Path to the directory containing files
            recursive: Whether to process subdirectories
            metadata: Additional metadata to add to all documents

        Returns:
            List of processed documents and a processing report
        """
        if not os.path.isdir(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")

        # Initialize processing report
        report = {
            "summary": {
                "total_files": 0,
                "successful": 0,
                "unreadable": 0,
                "language_detection_failures": 0,
                "files_with_warnings": 0
            },
            "details": [],
            "recommendations": {
                "files_to_review": [],
                "files_to_consider_removing": []
            }
        }

        documents = []

        # Get all files in the directory
        file_paths = []
        if recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_paths.append(os.path.join(root, file))
        else:
            file_paths = [os.path.join(directory_path, f) for f in os.listdir(directory_path)
                          if os.path.isfile(os.path.join(directory_path, f))]

        # Update total files count
        report["summary"]["total_files"] = len(file_paths)

        # Process each file
        for file_path in file_paths:
            file_extension = os.path.splitext(file_path)[1].lower().replace(".", "")

            # Skip unsupported file types
            if file_extension not in self.file_processor.supported_extensions:
                report["details"].append({
                    "file": file_path,
                    "status": "skipped",
                    "reason": f"Unsupported file type: {file_extension}"
                })
                continue

            try:
                # Process the file
                content, file_metadata = await self.file_processor.process_file(file_path)

                # Add additional metadata if provided
                if metadata:
                    file_metadata.update(metadata)

                # Create document entity
                document = Document(
                    content=content,
                    metadata=file_metadata
                )

                # Add to list of documents
                documents.append(document)

                # Update successful count
                report["summary"]["successful"] += 1

                # Add to details
                report["details"].append({
                    "file": file_path,
                    "status": "success",
                    "content_length": len(content),
                    "metadata": file_metadata
                })

            except Exception as e:
                # Update unreadable count
                report["summary"]["unreadable"] += 1
                report["summary"]["files_with_warnings"] += 1

                # Add to details
                report["details"].append({
                    "file": file_path,
                    "status": "error",
                    "reason": str(e)
                })

                # Add to files to review
                report["recommendations"]["files_to_review"].append({
                    "file": file_path,
                    "reason": f"Error processing file: {str(e)}"
                })

        # Perform language detection and add to report
        for document in documents:
            try:
                # Detect language (in a real implementation, this would use a language detection service)
                # For now, we'll just assume English
                document.metadata["language"] = "en"
            except Exception as e:
                # Update language detection failures count
                report["summary"]["language_detection_failures"] += 1
                report["summary"]["files_with_warnings"] += 1

                # Add to files to review
                report["recommendations"]["files_to_review"].append({
                    "file": document.metadata.get("source", "unknown"),
                    "reason": f"Language detection failed: {str(e)}"
                })

        # Generate recommendations for files to consider removing
        for detail in report["details"]:
            if detail["status"] == "success":
                # If content is very short, recommend reviewing
                if detail.get("content_length", 0) < 100:
                    report["recommendations"]["files_to_consider_removing"].append({
                        "file": detail["file"],
                        "reason": f"Very short content (only {detail['content_length']} characters)"
                    })

        return documents, report

    async def analyze_document_quality(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Analyze the quality of documents for RAG.

        Args:
            documents: List of documents to analyze

        Returns:
            Quality analysis report
        """
        # Initialize quality analysis report
        quality_analysis = {
            "content_length": {
                "average": 0,
                "min": float("inf"),
                "max": 0,
                "distribution": {
                    "very_short": 0,  # < 200 chars
                    "short": 0,  # 200-1000 chars
                    "medium": 0,  # 1000-5000 chars
                    "long": 0,  # 5000-20000 chars
                    "very_long": 0  # > 20000 chars
                }
            },
            "language_distribution": {},
            "recommendations": {
                "improve_chunking": False,
                "consider_filtering": False,
                "review_long_documents": False
            }
        }

        if not documents:
            return quality_analysis

        # Calculate content length statistics
        total_length = 0
        for doc in documents:
            content_length = len(doc.content)
            total_length += content_length

            # Update min/max
            quality_analysis["content_length"]["min"] = min(quality_analysis["content_length"]["min"], content_length)
            quality_analysis["content_length"]["max"] = max(quality_analysis["content_length"]["max"], content_length)

            # Update distribution
            if content_length < 200:
                quality_analysis["content_length"]["distribution"]["very_short"] += 1
            elif content_length < 1000:
                quality_analysis["content_length"]["distribution"]["short"] += 1
            elif content_length < 5000:
                quality_analysis["content_length"]["distribution"]["medium"] += 1
            elif content_length < 20000:
                quality_analysis["content_length"]["distribution"]["long"] += 1
            else:
                quality_analysis["content_length"]["distribution"]["very_long"] += 1

            # Update language distribution
            language = doc.metadata.get("language", "unknown")
            if language in quality_analysis["language_distribution"]:
                quality_analysis["language_distribution"][language] += 1
            else:
                quality_analysis["language_distribution"][language] = 1

        # Calculate average content length
        quality_analysis["content_length"]["average"] = total_length / len(documents)

        # Generate recommendations
        if quality_analysis["content_length"]["distribution"]["very_long"] > 0:
            quality_analysis["recommendations"]["improve_chunking"] = True
            quality_analysis["recommendations"]["review_long_documents"] = True

        if quality_analysis["content_length"]["distribution"]["very_short"] > len(documents) * 0.2:
            quality_analysis["recommendations"]["consider_filtering"] = True

        return quality_analysis

    async def vectorize_files(
            self,
            file_paths: List[str],
            theme_id: str,
            batch_size: int = 100
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate embeddings for files and store in vector database.

        Args:
            file_paths: List of file paths to vectorize
            theme_id: ID of the theme to associate with the embeddings
            batch_size: Number of documents to process in a batch

        Returns:
            List of embedding results and a vectorization report
        """
        # Initialize vectorization report
        report = {
            "summary": {
                "total_files": len(file_paths),
                "successful": 0,
                "unreadable": 0,
                "language_detection_failures": 0,
                "files_with_warnings": 0,
                "embedding_failures": 0
            },
            "details": [],
            "recommendations": {
                "files_to_review": [],
                "files_to_consider_removing": []
            }
        }

        # Process files to get documents
        documents = []
        for file_path in file_paths:
            try:
                content, metadata = await self.file_processor.process_file(file_path)

                # Add theme ID to metadata
                metadata["theme_id"] = theme_id

                # Create document entity
                document = Document(
                    content=content,
                    metadata=metadata
                )

                documents.append(document)

                # Add to details
                report["details"].append({
                    "file": file_path,
                    "status": "processed",
                    "content_length": len(content)
                })

            except Exception as e:
                # Update unreadable count
                report["summary"]["unreadable"] += 1
                report["summary"]["files_with_warnings"] += 1

                # Add to details
                report["details"].append({
                    "file": file_path,
                    "status": "error",
                    "reason": str(e)
                })

                # Add to files to review
                report["recommendations"]["files_to_review"].append({
                    "file": file_path,
                    "reason": f"Error processing file: {str(e)}"
                })

        # Process documents in batches
        embedding_results = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            try:
                # Generate embeddings
                embeddings = await self.embedding_service.get_embeddings([doc.content for doc in batch])

                # Store documents and embeddings
                for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                    # Store document in document store
                    doc_id = await self.document_store.store_document(doc)

                    # Store embedding in vector index
                    vector_id = await self.vector_index.add_vectors([embedding], [doc_id])

                    # Add to results
                    embedding_results.append({
                        "document_id": doc_id,
                        "vector_id": vector_id[0] if vector_id else None,
                        "source": doc.metadata.get("source"),
                        "theme_id": theme_id
                    })

                    # Update successful count
                    report["summary"]["successful"] += 1

                    # Update detail status
                    if j < len(report["details"]):
                        report["details"][i + j]["status"] = "vectorized"
                        report["details"][i + j]["document_id"] = doc_id
                        report["details"][i + j]["vector_id"] = vector_id[0] if vector_id else None

            except Exception as e:
                # Update embedding failures count
                report["summary"]["embedding_failures"] += len(batch)
                report["summary"]["files_with_warnings"] += len(batch)

                # Update detail status for all documents in batch
                for j in range(len(batch)):
                    if i + j < len(report["details"]):
                        report["details"][i + j]["status"] = "embedding_error"
                        report["details"][i + j]["reason"] = str(e)

                # Add to files to review
                for doc in batch:
                    report["recommendations"]["files_to_review"].append({
                        "file": doc.metadata.get("source", "unknown"),
                        "reason": f"Embedding generation failed: {str(e)}"
                    })

        return embedding_results, report

    async def get_vectorization_status(self, theme_id: str) -> Dict[str, Any]:
        """
        Get the vectorization status for a theme.

        Args:
            theme_id: ID of the theme to check

        Returns:
            Status information about the theme's vectorization
        """
        # This would typically query your document store and vector index
        # For now, we'll return a simulated status

        # Get count of all documents for this theme
        total_docs = await self.document_store.count_documents({"theme_id": theme_id})

        # Get count of documents with embeddings
        vectorized_docs = await self.vector_index.count_vectors({"theme_id": theme_id})

        percent_complete = (vectorized_docs / total_docs * 100) if total_docs > 0 else 0

        # Determine status
        status = "not_started"
        if vectorized_docs > 0:
            if vectorized_docs == total_docs:
                status = "complete"
            else:
                status = "in_progress"

        return {
            "total_files": total_docs,
            "vectorized_files": vectorized_docs,
            "percent_complete": percent_complete,
            "status": status,
            "vector_db_info": {
                "type": self.vector_index.get_index_type(),
                "dimensions": self.vector_index.get_dimensions()
            },
            "last_updated": datetime.now().isoformat()
        }