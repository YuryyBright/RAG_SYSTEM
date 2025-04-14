# app/core/services/chunking_service.py
from typing import List, Dict, Any, Optional, Tuple
import re


class ChunkingService:
    """Service for chunking text documents into smaller segments for embedding."""

    def __init__(
            self,
            default_chunk_size: int = 1000,
            default_chunk_overlap: int = 200,
            default_separator: str = "\n"
    ):
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.default_separator = default_separator

    def chunk_text(
            self,
            text: str,
            chunk_size: Optional[int] = None,
            chunk_overlap: Optional[int] = None,
            separator: Optional[str] = None
    ) -> List[str]:
        """
        Split text into overlapping chunks of specified size.

        Parameters:
        -----------
        text : str
            The text to split into chunks
        chunk_size : int, optional
            The maximum size of each chunk (in characters)
        chunk_overlap : int, optional
            The number of characters to overlap between chunks
        separator : str, optional
            The character(s) to use as potential split points

        Returns:
        --------
        List[str]
            List of text chunks
        """
        # Use defaults if not specified
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        separator = separator or self.default_separator

        # If text is shorter than chunk_size, return it as a single chunk
        if len(text) <= chunk_size:
            return [text]

        # Split the text by the separator
        splits = text.split(separator)

        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            # Add the separator back to the split (except for the first one)
            if split and current_chunk:
                split_with_sep = separator + split
            else:
                split_with_sep = split

            # If adding this split would exceed the chunk size, finalize the chunk
            if current_length + len(split_with_sep) > chunk_size and current_chunk:
                # Join the current chunk and add it to the list of chunks
                chunks.append(''.join(current_chunk))

                # Create overlap by keeping some of the current chunk
                overlap_text = ''.join(current_chunk[-chunk_overlap:]) if chunk_overlap > 0 else ""
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)

            # Add the current split to the chunk
            if split_with_sep:
                current_chunk.append(split_with_sep)
                current_length += len(split_with_sep)

        # Add the final chunk if it's not empty
        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks

    def chunk_by_semantic_units(
            self,
            text: str,
            min_chunk_size: int = 500,
            max_chunk_size: int = 1500,
            separator_hierarchy: Optional[List[str]] = None
    ) -> List[str]:
        """
        Split text by semantic units, attempting to keep coherent sections together.

        Parameters:
        -----------
        text : str
            The text to split into chunks
        min_chunk_size : int
            The minimum size of each chunk (in characters)
        max_chunk_size : int
            The maximum size of each chunk (in characters)
        separator_hierarchy : List[str], optional
            Ordered list of separators to use, from highest to lowest priority

        Returns:
        --------
        List[str]
            List of text chunks
        """
        # Default separator hierarchy if not provided
        if not separator_hierarchy:
            separator_hierarchy = [
                "\n## ",  # Markdown h2
                "\n### ",  # Markdown h3
                "\n\n",  # Paragraph
                ". ",  # Sentence
                ", ",  # Clause
                " "  # Word
            ]

        # If text is shorter than max_chunk_size, return it as a single chunk
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        for separator in separator_hierarchy:
            result = self._try_chunking_with_separator(
                text, separator, min_chunk_size, max_chunk_size
            )

            if result:
                # This separator worked well
                chunks = result
                break

        # If no separator worked well, fall back to simple chunking
        if not chunks:
            chunks = self.chunk_text(
                text,
                chunk_size=max_chunk_size,
                chunk_overlap=min(200, max_chunk_size // 5)
            )

        return chunks

    def _try_chunking_with_separator(
            self,
            text: str,
            separator: str,
            min_chunk_size: int,
            max_chunk_size: int
    ) -> Optional[List[str]]:
        """
        Try chunking the text with a specific separator.
        Returns None if the separator doesn't work well for this text.
        """
        # Split by separator
        segments = text.split(separator)

        # If most segments are too small or too large, this separator isn't suitable
        segment_sizes = [len(s) for s in segments]
        too_small = sum(1 for size in segment_sizes if size < min_chunk_size / 2)
        too_large = sum(1 for size in segment_sizes if size > max_chunk_size * 0.8)

        # If more than 70% of segments are too small or too large, try another separator
        if (too_small + too_large) / len(segments) > 0.7:
            return None

        # This separator seems good, proceed with chunking
        chunks = []
        current_chunk = []
        current_length = 0

        for i, segment in enumerate(segments):
            # Add separator back to segment (except for first one)
            if i > 0:
                segment_with_sep = separator + segment
            else:
                segment_with_sep = segment

            segment_length = len(segment_with_sep)

            # If segment alone exceeds max_chunk_size, we need to split it further
            if segment_length > max_chunk_size:
                # First add the current accumulated chunk if it exists
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Then recursively chunk this large segment and add the results
                sub_chunks = self.chunk_text(
                    segment_with_sep,
                    chunk_size=max_chunk_size,
                    chunk_overlap=min(200, max_chunk_size // 5)
                )
                chunks.extend(sub_chunks)
                continue

            # If adding this segment would exceed max_chunk_size, finalize current chunk
            if current_length + segment_length > max_chunk_size and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_length = 0

            # Add segment to current chunk
            current_chunk.append(segment_with_sep)
            current_length += segment_length

            # If current chunk exceeds min_chunk_size and segment ends with sentence-ending punctuation,
            # consider this a good place to break
            last_char = segment_with_sep.strip()[-1] if segment_with_sep.strip() else None
            if current_length > min_chunk_size and last_char in ['.', '!', '?', ':', ';']:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_length = 0

        # Add the final chunk if it's not empty
        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks