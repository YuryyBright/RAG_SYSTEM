"""
Utility functions for text processing in the RAG system including
tokenization, normalization, text chunking, and other text manipulations.
"""
import re
import string
import unicodedata
from typing import List, Dict, Optional, Tuple, Any, Callable, Union
import logging
from collections import Counter

# Optional imports - install these packages if needed
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import spacy

    SPACY_AVAILABLE = False  # Will be set to True after loading a model
    nlp = None
except ImportError:
    SPACY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_LANGUAGE = "english"


def initialize_nltk():
    """Initialize NLTK by downloading required resources."""
    if not NLTK_AVAILABLE:
        logger.warning("NLTK is not installed. Some text processing features will be limited.")
        return

    try:
        # Download necessary NLTK data
        for resource in ["punkt", "stopwords"]:
            try:
                nltk.data.find(f"tokenizers/{resource}")
            except LookupError:
                nltk.download(resource, quiet=True)
    except Exception as e:
        logger.error(f"Failed to initialize NLTK: {str(e)}")


def initialize_spacy(model_name="en_core_web_sm"):
    """Initialize spaCy with specified model."""
    global nlp, SPACY_AVAILABLE

    if not 'spacy' in globals():
        logger.warning("spaCy is not installed. Some text processing features will be limited.")
        return

    try:
        nlp = spacy.load(model_name)
        SPACY_AVAILABLE = True
    except Exception as e:
        logger.error(f"Failed to load spaCy model '{model_name}': {str(e)}")
        try:
            # Try to download the model
            import subprocess
            subprocess.run([
                "python", "-m", "spacy", "download", model_name
            ], check=True)
            nlp = spacy.load(model_name)
            SPACY_AVAILABLE = True
        except Exception as download_error:
            logger.error(f"Failed to download spaCy model: {str(download_error)}")
            SPACY_AVAILABLE = False


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace, converting to lowercase,
    and performing unicode normalization.

    Args:
        text: Input text

    Returns:
        str: Normalized text
    """
    # Unicode normalization
    text = unicodedata.normalize("NFKD", text)

    # Convert to lowercase
    text = text.lower()

    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading and trailing whitespace
    text = text.strip()

    return text


def remove_punctuation(text: str) -> str:
    """
    Remove punctuation from text.

    Args:
        text: Input text

    Returns:
        str: Text with punctuation removed
    """
    translator = str.maketrans('', '', string.punctuation)
    return text.translate(translator)


def remove_stopwords(text: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Remove stopwords from text.

    Args:
        text: Input text
        language: Language for stopwords

    Returns:
        str: Text with stopwords removed
    """
    if not NLTK_AVAILABLE:
        logger.warning("NLTK is not available. Stopwords cannot be removed.")
        return text

    try:
        stop_words = set(stopwords.words(language))
        words = word_tokenize(text)
        filtered_words = [word for word in words if word.lower() not in stop_words]
        return ' '.join(filtered_words)
    except Exception as e:
        logger.error(f"Error removing stopwords: {str(e)}")
        return text


def chunk_text_by_tokens(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[str]:
    """
    Split text into chunks based on token count.

    Args:
        text: Input text
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Number of overlapping tokens between chunks

    Returns:
        List[str]: List of text chunks
    """
    if not NLTK_AVAILABLE:
        # Fallback to simple word-based chunking
        words = text.split()
        chunks = []

        if len(words) <= chunk_size:
            return [text]

        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    # Use NLTK for better tokenization
    tokens = word_tokenize(text)
    chunks = []

    if len(tokens) <= chunk_size:
        return [text]

    for i in range(0, len(tokens), chunk_size - chunk_overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk = ' '.join(chunk_tokens)
        chunks.append(chunk)

    return chunks


def chunk_text_by_sentences(
        text: str,
        max_sentences: int = 10,
        overlap_sentences: int = 2
) -> List[str]:
    """
    Split text into chunks based on sentence count.

    Args:
        text: Input text
        max_sentences: Maximum sentences per chunk
        overlap_sentences: Number of overlapping sentences between chunks

    Returns:
        List[str]: List of text chunks
    """
    if not NLTK_AVAILABLE:
        # Simple sentence splitting as fallback
        sentences = re.split(r'(?<=[.!?])\s+', text)
    else:
        sentences = sent_tokenize(text)

    chunks = []

    if len(sentences) <= max_sentences:
        return [text]

    for i in range(0, len(sentences), max_sentences - overlap_sentences):
        chunk = ' '.join(sentences[i:i + max_sentences])
        chunks.append(chunk)

    return chunks


def chunk_text_by_paragraphs(text: str, max_paragraphs: int = 3) -> List[str]:
    """
    Split text into chunks based on paragraph breaks.

    Args:
        text: Input text
        max_paragraphs: Maximum paragraphs per chunk

    Returns:
        List[str]: List of text chunks
    """
    # Split by double newline (paragraph break)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if len(paragraphs) <= max_paragraphs:
        return [text]

    chunks = []
    for i in range(0, len(paragraphs), max_paragraphs):
        chunk = '\n\n'.join(paragraphs[i:i + max_paragraphs])
        chunks.append(chunk)

    return chunks


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract most significant keywords from text.

    Args:
        text: Input text
        top_n: Number of keywords to extract

    Returns:
        List[str]: List of keywords
    """
    if SPACY_AVAILABLE and nlp:
        doc = nlp(text)
        # Extract noun phrases and named entities
        keywords = []

        # Add named entities
        for ent in doc.ents:
            keywords.append(ent.text.lower())

        # Add noun chunks
        for chunk in doc.noun_chunks:
            keywords.append(chunk.text.lower())

        # Count and sort keywords
        keyword_counter = Counter(keywords)
        return [keyword for keyword, _ in keyword_counter.most_common(top_n)]

    elif NLTK_AVAILABLE:
        # Fallback to simple frequency analysis with NLTK
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words(DEFAULT_LANGUAGE))

        # Filter out stopwords and short words
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

        # Count and return top words
        word_counter = Counter(filtered_words)
        return [word for word, _ in word_counter.most_common(top_n)]

    else:
        # Very basic approach without NLP libraries
        words = text.lower().split()
        word_counter = Counter(words)
        return [word for word, _ in word_counter.most_common(top_n) if len(word) > 3]


def extract_sentences_with_keyword(text: str, keyword: str, context_size: int = 1) -> List[str]:
    """
    Extract sentences containing a specific keyword with surrounding context.

    Args:
        text: Input text
        keyword: Keyword to search for
        context_size: Number of surrounding sentences to include

    Returns:
        List[str]: List of sentence contexts
    """
    if not NLTK_AVAILABLE:
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
    else:
        sentences = sent_tokenize(text)

    results = []
    keyword_lower = keyword.lower()

    for i, sentence in enumerate(sentences):
        if keyword_lower in sentence.lower():
            # Get context sentences
            start = max(0, i - context_size)
            end = min(len(sentences), i + context_size + 1)
            context = ' '.join(sentences[start:end])
            results.append(context)

    return results


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.

    Args:
        text: Input text

    Returns:
        List[str]: List of URLs
    """
    url_pattern = r'https?://[^\s)>]+'
    return re.findall(url_pattern, text)


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.

    Args:
        text: Input text

    Returns:
        List[str]: List of email addresses
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)


def clean_html(html_text: str) -> str:
    """
    Remove HTML tags from text.

    Args:
        html_text: Text containing HTML

    Returns:
        str: Clean text without HTML tags
    """
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_text)

    # Handle common HTML entities
    clean_text = re.sub(r'&nbsp;', ' ', clean_text)
    clean_text = re.sub(r'&lt;', '<', clean_text)
    clean_text = re.sub(r'&gt;', '>', clean_text)
    clean_text = re.sub(r'&amp;', '&', clean_text)
    clean_text = re.sub(r'&quot;', '"', clean_text)
    clean_text = re.sub(r'&#39;', "'", clean_text)

    # Normalize whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text)

    return clean_text.strip()


def get_text_stats(text: str) -> Dict[str, Any]:
    """
    Get basic statistics about the text.

    Args:
        text: Input text

    Returns:
        Dict[str, Any]: Text statistics
    """
    # Character count
    char_count = len(text)

    # Word count
    words = text.split()
    word_count = len(words)

    # Sentence count
    if NLTK_AVAILABLE:
        sentences = sent_tokenize(text)
    else:
        sentences = re.split(r'(?<=[.!?])\s+', text)
    sentence_count = len(sentences)

    # Average word length
    avg_word_length = sum(len(word) for word in words) / max(1, word_count)

    # Average sentence length (in words)
    avg_sentence_length = word_count / max(1, sentence_count)

    return {
        "character_count": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "average_word_length": round(avg_word_length, 2),
        "average_sentence_length": round(avg_sentence_length, 2)
    }


def find_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple text similarity using word overlap.
    For more advanced similarity, use an embedding model.

    Args:
        text1: First text
        text2: Second text

    Returns:
        float: Similarity score between 0 and 1
    """
    # Normalize and tokenize texts
    if NLTK_AVAILABLE:
        words1 = set(word_tokenize(text1.lower()))
        words2 = set(word_tokenize(text2.lower()))
    else:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / max(1, union)