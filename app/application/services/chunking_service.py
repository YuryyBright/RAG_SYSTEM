# app/core/services/chunking_service.py
from typing import List, Dict, Any, Optional, Tuple
# import tiktoken

class ChunkingService:
    """Service for chunking text documents into smaller segments for embedding."""

    def __init__(self, default_chunk_size=2000, default_chunk_overlap=250, default_separator="\n"):
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

        for i, split in enumerate(splits):
            # Add the separator back to the split (except for the first one)
            if split and i > 0:
                split_with_sep = separator + split
            else:
                split_with_sep = split

            # If adding this split would exceed the chunk size, finalize the chunk
            if current_length + len(split_with_sep) > chunk_size and current_chunk:
                # Join the current chunk and add it to the list of chunks
                chunks.append(''.join(current_chunk))

                # Find a good overlap point that doesn't cut in the middle of semantic units
                if chunk_overlap > 0:
                    # Calculate overlap starting point
                    overlap_start_idx = max(0, len(''.join(current_chunk)) - chunk_overlap)

                    # Find the closest separator after the overlap starting point
                    overlap_text = ''.join(current_chunk)
                    last_separator_pos = -1

                    for sep_pos in [pos for pos in range(len(overlap_text)) if overlap_text.startswith(separator, pos)]:
                        if sep_pos >= overlap_start_idx:
                            last_separator_pos = sep_pos
                            break

                    # If we found a good separator position, use it; otherwise use character-based overlap
                    if last_separator_pos >= 0:
                        overlap_text = overlap_text[last_separator_pos:]
                    else:
                        overlap_text = overlap_text[overlap_start_idx:]

                    current_chunk = [overlap_text] if overlap_text else []
                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

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
            chunk_size: Optional[int] = None,
            chunk_overlap: Optional[int] = None,
            separator_hierarchy: Optional[List[str]] = None
    ) -> List[str]:
        """
        Split text by semantic units, attempting to keep coherent sections together.

        Parameters:
        -----------
        text : str
            The text to split into chunks
        chunk_size : int, optional
            The target maximum size of each chunk (in characters)
        chunk_overlap : int, optional
            The target overlap between chunks (in characters)
        separator_hierarchy : List[str], optional
            Ordered list of separators to use, from highest to lowest priority

        Returns:
        --------
        List[str]
            List of text chunks
        """
        # Use defaults if not specified
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap

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

        # If text is shorter than chunk_size, return it as a single chunk
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        remaining_text = text

        # Try each separator in the hierarchy
        for separator in separator_hierarchy:
            if not remaining_text:
                break

            result = self._try_chunking_with_separator(
                remaining_text, separator, chunk_size, chunk_overlap
            )

            if result:
                # Add successfully chunked sections to our chunks list
                chunks.extend(result)
                remaining_text = ""

        # If we still have remaining text, fall back to character-based chunking
        if remaining_text:
            chunks.extend(self.chunk_text(
                remaining_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator=" "  # Fall back to word-level splitting
            ))

        return chunks

    def _try_chunking_with_separator(
            self,
            text: str,
            separator: str,
            chunk_size: int,
            chunk_overlap: int
    ) -> List[str]:
        """
        Attempt to chunk text using a specific separator.

        Parameters:
        -----------
        text : str
            The text to chunk
        separator : str
            The separator to use for chunking
        chunk_size : int
            Target maximum chunk size
        chunk_overlap : int
            Target overlap between chunks

        Returns:
        --------
        List[str] or None
            List of chunks if successful, None if the separator doesn't create good chunks
        """
        # Split by the separator
        splits = text.split(separator)

        # If this separator doesn't create meaningful splits, return None
        if len(splits) <= 1:
            return None

        chunks = []
        current_chunk = []
        current_length = 0

        for i, split in enumerate(splits):
            # Add separator back except for the first item
            if i > 0 and split:
                split_with_sep = separator + split
            else:
                split_with_sep = split

            split_length = len(split_with_sep)

            # If a single split is larger than chunk_size, this separator won't work well
            if split_length > chunk_size * 1.5:
                return None

            # If adding this split would exceed the chunk size, finalize the chunk
            if current_length + split_length > chunk_size and current_chunk:
                # Don't create tiny chunks - require at least 50% of chunk_size
                if current_length < chunk_size * 0.5 and len(chunks) > 0:
                    # Merge with the previous chunk if possible
                    if chunks:
                        chunks[-1] += ''.join(current_chunk)
                    else:
                        chunks.append(''.join(current_chunk))
                else:
                    chunks.append(''.join(current_chunk))

                # Calculate overlap, ensuring we don't overlap at arbitrary positions
                if chunk_overlap > 0 and current_chunk:
                    full_chunk_text = ''.join(current_chunk)

                    # Find the last complete semantic unit within the overlap range
                    overlap_start = max(0, len(full_chunk_text) - chunk_overlap)

                    # Find the nearest separator after the overlap start
                    nearest_sep_pos = full_chunk_text.find(separator, overlap_start)

                    if nearest_sep_pos != -1:
                        # Use separator-based overlap
                        overlap_text = full_chunk_text[nearest_sep_pos:]
                    else:
                        # Fall back to character-based overlap if no separator found
                        overlap_text = full_chunk_text[overlap_start:]

                    current_chunk = [overlap_text]
                    current_length = len(overlap_text)
                else:
                    current_chunk = []
                    current_length = 0

            # Add the current split to the chunk
            current_chunk.append(split_with_sep)
            current_length += split_length

        # Add the final chunk
        if current_chunk:
            chunks.append(''.join(current_chunk))

        # Validate the chunks - ensure we've properly chunked the text
        total_chunks_length = sum(len(chunk) for chunk in chunks)
        expected_length = len(text) + (len(chunks) - 1) * chunk_overlap

        # Allow for small differences due to overlap calculation
        if abs(total_chunks_length - expected_length) > len(chunks) * 10:
            return None

        return chunks