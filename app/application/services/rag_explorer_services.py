from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import json

from domain.entities.document import Document
from modules.storage.document_store import DocumentStore
from utils.logger_util import get_logger

logger = get_logger(__name__)


class RAGExplorer:
    """
    Utility class to explore and provide information about the RAG document structure.

    Provides methods to list files, summarize document collections, and generate stats
    about the documents stored in the RAG system.
    """

    def __init__(self, document_store: DocumentStore):
        """
        Initialize the RAG Explorer with a document store.

        Args:
            document_store: The document store containing RAG documents
        """
        self.document_store = document_store
        self.storage_path = document_store.storage_path

    async def list_structure(self,
                             owner_id: Optional[str] = None,
                             theme_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List the structure of documents in the RAG system.

        Args:
            owner_id: Optional filter by owner ID
            theme_id: Optional filter by theme ID

        Returns:
            Dict containing the structure information:
                - owners: List of owner IDs or filtered owner
                - themes: Mapping of themes to document counts
                - document_count: Total document count
                - file_stats: Information about file types and sizes
        """
        structure = {
            "owners": [],
            "themes": {},
            "document_count": 0,
            "file_stats": {
                "types": {},
                "size_total": 0,
                "avg_document_size": 0
            }
        }

        # Check if storage path exists
        if not os.path.exists(self.storage_path):
            return structure

        # Get owners (directories in storage path)
        owners = []
        if owner_id:
            # If specific owner requested, only include that one if it exists
            owner_path = self.storage_path / owner_id
            if os.path.exists(owner_path):
                owners = [owner_id]
        else:
            # Otherwise get all owners
            try:
                owners = [d.name for d in os.scandir(self.storage_path) if d.is_dir()]
            except Exception as e:
                logger.error(f"Error scanning storage path: {str(e)}")

        structure["owners"] = owners

        # Process each owner's themes and documents
        total_doc_count = 0
        total_size = 0
        file_extensions = {}

        for owner in owners:
            owner_path = self.storage_path / owner

            # Get themes for this owner
            themes = []
            if theme_id:
                # If specific theme requested, only include that one if it exists
                theme_path = owner_path / theme_id
                if os.path.exists(theme_path):
                    themes = [theme_id]
            else:
                # Otherwise get all themes for this owner
                try:
                    themes = [d.name for d in os.scandir(owner_path) if d.is_dir()]
                except Exception as e:
                    logger.error(f"Error scanning owner path {owner}: {str(e)}")
                    continue

            # Process each theme
            for theme in themes:
                theme_path = owner_path / theme

                # Count documents in this theme
                doc_files = []
                try:
                    doc_files = [f for f in os.listdir(theme_path) if
                                 f.endswith('.json') and not f.endswith('.embedding.json')]
                except Exception as e:
                    logger.error(f"Error listing theme directory {theme}: {str(e)}")
                    continue

                doc_count = len(doc_files)
                total_doc_count += doc_count

                # Store theme info
                theme_key = f"{owner}/{theme}"
                structure["themes"][theme_key] = {
                    "document_count": doc_count,
                    "sample_docs": doc_files[:5] if doc_count > 0 else []
                }

                # Process file stats
                for file in doc_files:
                    file_path = theme_path / file
                    if os.path.isfile(file_path):
                        # Get file extension
                        _, ext = os.path.splitext(file)
                        ext = ext.lower()
                        file_extensions[ext] = file_extensions.get(ext, 0) + 1

                        # Get file size
                        try:
                            size = os.path.getsize(file_path)
                            total_size += size
                        except Exception:
                            pass

        # Finalize structure information
        structure["document_count"] = total_doc_count
        structure["file_stats"]["types"] = file_extensions
        structure["file_stats"]["size_total"] = total_size
        if total_doc_count > 0:
            structure["file_stats"]["avg_document_size"] = total_size / total_doc_count

        return structure

    async def get_document_metadata_summary(self,
                                            owner_id: Optional[str] = None,
                                            theme_id: Optional[str] = None,
                                            limit: int = 100) -> Dict[str, Any]:
        """
        Get a summary of document metadata in the RAG system.

        Args:
            owner_id: Optional filter by owner ID
            theme_id: Optional filter by theme ID
            limit: Maximum number of documents to analyze

        Returns:
            Dict containing metadata summary:
                - metadata_keys: Common metadata keys and their frequencies
                - content_sample: Sample of document content (first 100 chars)
                - document_count: Number of documents analyzed
        """
        # Fetch documents from repository
        documents = []

        if owner_id and theme_id:
            # Use document store methods to get documents by theme
            filter_criteria = {"owner_id": owner_id, "theme_id": theme_id}
            # We might need a new method in document_store for this specific query
            # For now, we'll use get_all and filter manually
            all_docs = await self.document_store.get_all(owner_id)
            documents = [doc for doc in all_docs if doc.theme_id == theme_id][:limit]
        elif owner_id:
            documents = (await self.document_store.get_all(owner_id))[:limit]
        else:
            documents = (await self.document_store.get_all())[:limit]

        if not documents:
            return {
                "metadata_keys": {},
                "content_sample": [],
                "document_count": 0
            }

        # Analyze metadata
        metadata_keys = {}
        content_samples = []

        for doc in documents:
            # Collect metadata keys
            if doc.metadata:
                for key in doc.metadata.keys():
                    metadata_keys[key] = metadata_keys.get(key, 0) + 1

            # Collect content samples (first 100 chars)
            if doc.content:
                sample = doc.content[:100] + ("..." if len(doc.content) > 100 else "")
                content_samples.append({
                    "id": doc.id,
                    "sample": sample
                })

        return {
            "metadata_keys": metadata_keys,
            "content_sample": content_samples[:5],  # Limit to 5 samples
            "document_count": len(documents)
        }

    async def search_structure(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search for documents matching a query and return structural information.

        Args:
            query: Text query to search for
            limit: Maximum number of results

        Returns:
            Dict containing search results and structure info
        """
        # Use document store's search capability
        query_embedding = await self.document_store.embedding_service.get_embedding(query)
        results = await self.document_store.semantic_search(
            query_embedding=query_embedding,
            limit=limit
        )

        # Group results by theme
        grouped_results = {}

        for doc in results:
            theme_key = f"{doc.owner_id}/{doc.theme_id}" if doc.theme_id else doc.owner_id
            if theme_key not in grouped_results:
                grouped_results[theme_key] = []

            grouped_results[theme_key].append({
                "id": doc.id,
                "title": doc.metadata.get("title", "Untitled"),
                "score": getattr(doc, "score", None),
                "snippet": doc.content[:200] + ("..." if len(doc.content) > 200 else "")
            })

        return {
            "query": query,
            "results_by_theme": grouped_results,
            "total_results": len(results)
        }

    def format_structure_response(self, structure: Dict[str, Any]) -> str:
        """
        Format structure information into a readable string response.

        Args:
            structure: Structure information from list_structure

        Returns:
            Formatted string describing the RAG structure
        """
        lines = ["Your RAG system contains the following structure:"]

        # Add document count
        lines.append(f"\nTotal documents: {structure['document_count']}")

        # Add owners
        lines.append(f"\nOwners ({len(structure['owners'])}): {', '.join(structure['owners'])}")

        # Add themes
        lines.append(f"\nThemes ({len(structure['themes'])}):")
        for theme_key, theme_data in structure['themes'].items():
            sample_docs = ', '.join(theme_data['sample_docs'][:3])
            if theme_data['sample_docs'] and len(theme_data['sample_docs']) > 3:
                sample_docs += f"... (and {len(theme_data['sample_docs']) - 3} more)"
            lines.append(f"  - {theme_key}: {theme_data['document_count']} documents")
            if sample_docs:
                lines.append(f"    Sample files: {sample_docs}")

        # Add file stats
        lines.append("\nFile statistics:")
        total_mb = structure['file_stats']['size_total'] / (1024 * 1024)
        lines.append(f"  - Total size: {total_mb:.2f} MB")

        if structure['document_count'] > 0:
            avg_kb = (structure['file_stats']['avg_document_size'] / 1024)
            lines.append(f"  - Average document size: {avg_kb:.2f} KB")

        # Add file types
        if structure['file_stats']['types']:
            lines.append("  - File types:")
            for ext, count in structure['file_stats']['types'].items():
                lines.append(f"    - {ext}: {count} files")

        return "\n".join(lines)