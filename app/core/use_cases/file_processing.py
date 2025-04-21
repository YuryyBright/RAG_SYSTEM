# app/core/use_cases/file_processing.py
import os
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import numpy as np
from adapters.storage.document_store import DocumentStore

from app.core.entities.document import Document
from core.interfaces.embedding import EmbeddingInterface
from core.services.chunking_service import ChunkingService
from core.services.vector_index_services import VectorIndexService
from infrastructure.loaders.file_processor import FileProcessor
from utils.logger_util import get_logger
from api.websockets.task_updates import TaskUpdateManager

logger = get_logger(__name__)




class FileProcessingUseCase:
    """
    Use case for processing, chunking, and vectorizing files in the RAG system.
    """

    def __init__(
            self,
            file_processor: FileProcessor,
            chunking_service: ChunkingService,
            embedding_service: EmbeddingInterface,
            document_store: DocumentStore,
            vector_index: VectorIndexService,
            task_update_manager: TaskUpdateManager
    ):
        """
        Initialize the FileProcessingUseCase with required services.

        Parameters
        ----------
        file_processor : FileProcessor
            Responsible for reading/parsing files.
        chunking_service : ChunkingService
            Responsible for splitting text content into smaller chunks.
        embedding_service : EmbeddingService
            Responsible for generating vector embeddings for text chunks.
        document_store : DocumentStore
            Responsible for persisting documents and associated metadata.
        vector_index : VectorIndexService
            Responsible for storing/retrieving vectors and performing similarity searches.
        """
        self.file_processor = file_processor
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service
        self.document_store = document_store
        self.vector_index = vector_index
        self.task_update_manager = task_update_manager

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

    async def process_and_vectorize_directory(
            self,
            directory_path: str,
            recursive: bool = True,
            metadata: Dict[str, Any] = None,
            theme_id: str = None,
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
            task_id: str = None,
            user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Process all files in a directory:
           1) Reads each file in 'directory_path'
           2) Chunks the text
           3) Stores each chunk as a separate document
           4) Embeds each chunk
           5) Stores embeddings in the vector index
           6) Returns a consolidated report

        Also sends progress updates via WebSockets if task_id is provided.

        Parameters
        ----------
        directory_path : str
            Path to the directory containing files to process.
        recursive : bool
            Whether to process files in subdirectories.
        metadata : Dict[str, Any], optional
            Additional metadata to attach to documents.
        theme_id : str, optional
            Theme identifier, if you group documents under certain themes.
        chunk_size : int, optional
            Maximum size (in characters) of each text chunk (default 1000).
        chunk_overlap : int, optional
            Overlap (in characters) between consecutive text chunks (default 200).
        task_id : str, optional
            ID of the task to send progress updates for.
        user_id : str, optional
            ID of the user to send progress updates for.

        Returns
        -------
        Dict[str, Any]
            A report detailing how many files were processed, how many chunks
            were created, and any warnings or errors encountered.
        """
        READING = 0  # scan & load files
        CHUNKING = 1  # split text
        EMBEDDING = 2  # create & store vectors

        if not os.path.isdir(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")

        # Define progress ranges for each step
        READING_PROGRESS_START = 0
        READING_PROGRESS_END = 25
        CHUNKING_PROGRESS_START = 25
        CHUNKING_PROGRESS_END = 60
        EMBEDDING_PROGRESS_START = 60
        EMBEDDING_PROGRESS_END = 100

        # Step 1: Read directory and produce raw documents
        logger.info(f"Processing {directory_path}")

        # Create WebSocket update if task_id is provided
        if task_id:
            await self._send_task_update(
                task_id=task_id,
                theme_id=theme_id,
                user_id=user_id,
                status="in_progress",
                current_step=READING,
                progress=READING_PROGRESS_START,
                message="Starting processing reading files",
            )

        documents, base_report = await self.file_processor.process_directory(
            directory_path=directory_path,
            recursive=recursive,
            metadata=metadata,
        )

        # We'll extend that `base_report` to track chunking and embedding steps:
        extended_report = {
            "summary": {
                "total_files": base_report["summary"]["total_files"],
                "successful_files": base_report["summary"]["successful"],
                "unreadable_files": base_report["summary"]["unreadable"],
                "language_detection_failures": base_report["summary"]["language_detection_failures"],
                "files_with_warnings": base_report["summary"]["files_with_warnings"],
                "total_chunks_created": 0,
                "chunks_vectorized": 0
            },
            "details": base_report["details"],
            "recommendations": base_report["recommendations"],
        }

        if task_id:
            await self._send_task_update(
                task_id=task_id,
                theme_id=theme_id,
                user_id=user_id,
                status="in_progress",  # Changed from "completed" to "in_progress" since we're not done yet
                current_step=READING,
                progress=READING_PROGRESS_END,
                message=f"Finished processing {extended_report['summary']['total_files']} files: "
                        f"{extended_report['summary']['successful_files']} successful, "
                        f"{extended_report['summary']['unreadable_files']} unreadable, "
                        f"{extended_report['summary']['language_detection_failures']} language detection failures.",
            )

        # Step 2: Chunk, store, and embed each document
        total_chunks_created = 0
        chunks_vectorized = 0

        # We'll accumulate IDs for vector insertion
        vectors_to_add = []
        vector_ids = []

        # Update task to indicate chunking has started
        if task_id:
            await self._send_task_update(
                task_id=task_id,
                theme_id=theme_id,
                user_id=user_id,
                status="in_progress",
                current_step=CHUNKING,
                progress=CHUNKING_PROGRESS_START,
                message="Starting chunking process",
            )

        total_docs = len(documents)
        for idx, doc in enumerate(documents):
            text = doc.content
            # Use chunking service to split text
            chunks = self.chunking_service.chunk_text(
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            total_chunks_created += len(chunks)

            # Send periodic progress updates
            if task_id and idx % max(1, total_docs // 10) == 0:  # Update roughly every 10% of documents
                # Calculate progress within the chunking range
                chunk_progress_percent = idx / total_docs
                actual_progress = CHUNKING_PROGRESS_START + (
                            CHUNKING_PROGRESS_END - CHUNKING_PROGRESS_START) * chunk_progress_percent

                await self._send_task_update(
                    task_id=task_id,
                    theme_id=theme_id,
                    user_id=user_id,
                    status="in_progress",
                    current_step=CHUNKING,
                    progress=int(actual_progress),
                    message=f"Chunking document {idx + 1}/{total_docs}"
                )

            # For each chunk, treat it as a separate document
            for chunk in chunks:
                # Create a Document object for the chunk
                chunk_doc = Document(
                    content=chunk,
                    file_id=doc.file_id,
                    owner_id=doc.owner_id or doc.metadata.get("owner_id"),
                    theme_id=theme_id,
                    metadata={
                        **doc.metadata,  # copy original metadata
                        "theme_id": theme_id,
                        "parent_doc_id": doc.id,
                    }
                )
                # Store the chunk in the document store to get a doc_id
                doc_id = await self.document_store.store_document(chunk_doc)
                # We'll collect text for embedding
                vectors_to_add.append(chunk)
                vector_ids.append(doc_id)

        if task_id:
            await self._send_task_update(
                task_id=task_id,
                theme_id=theme_id,
                user_id=user_id,
                status="in_progress",
                current_step=CHUNKING,
                progress=CHUNKING_PROGRESS_END,
                message=f"Finished chunking {total_docs} documents into {total_chunks_created} chunks"
            )

        # Update task status for embedding step
        if task_id:
            await self._send_task_update(
                user_id=user_id,
                task_id=task_id,
                theme_id=theme_id,
                status="in_progress",
                current_step=EMBEDDING,
                progress=EMBEDDING_PROGRESS_START,
                message=f"Creating embeddings for {len(vectors_to_add)} chunks"
            )

        # Step 3: Embed all chunks in one or more batches
        if vectors_to_add:
            # For large sets, process in batches and update progress
            batch_size = 100  # Adjust based on your embedding service capacity
            total_batches = (len(vectors_to_add) + batch_size - 1) // batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, len(vectors_to_add))

                batch_vectors = vectors_to_add[start_idx:end_idx]
                batch_ids = vector_ids[start_idx:end_idx]

                embeddings = await self.embedding_service.get_embeddings(batch_vectors)
                await self.vector_index.add_vectors(embeddings, batch_ids)
                chunks_vectorized += len(batch_vectors)

                # Send progress updates for embedding process
                if task_id:
                    # Calculate progress within the embedding range
                    embedding_progress_percent = (batch_idx + 1) / total_batches
                    actual_progress = EMBEDDING_PROGRESS_START + (
                                EMBEDDING_PROGRESS_END - EMBEDDING_PROGRESS_START) * embedding_progress_percent

                    await self._send_task_update(
                        task_id=task_id,
                        theme_id=theme_id,
                        user_id=user_id,
                        status="in_progress",
                        current_step=EMBEDDING,
                        progress=int(actual_progress),
                        message=f"Processed batch {batch_idx + 1}/{total_batches} of embeddings"
                    )

        # Final task update
        if task_id:
            await self._send_task_update(
                task_id=task_id,
                theme_id=theme_id,
                user_id=user_id,
                status="completed",
                current_step=EMBEDDING,
                progress=EMBEDDING_PROGRESS_END,
                message="Processing complete"
            )

        # Update the extended report
        extended_report["summary"]["total_chunks_created"] = total_chunks_created
        extended_report["summary"]["chunks_vectorized"] = chunks_vectorized

        return extended_report

    async def _send_task_update(
            self,
            task_id: str,
            theme_id: str,
            user_id: str,
            status: str,
            current_step: int,
            progress: int,
            message: str | None = None,
    ):
        """Send a websocket update via TaskUpdateManager."""
        try:
            update_data = {
                "type": "task_update",
                "theme_id": theme_id,
                "user_id": user_id,
                "data": {
                    "id": task_id,
                    "status": status,
                    "current_step": current_step,
                    "progress": progress,
                    "message": message,
                },
            }
            await self.task_update_manager.broadcast_task_update(update_data)

        except Exception as e:
            logger.error(f"Failed to send task update: {e}")
            # Continue processing even if update fails



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