# app/api/schemas/files.py
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    """
    Schema for file response.

    Attributes
    ----------
    id : str
        The unique identifier of the file.
    filename : str
        The name of the file.
    content_type : str
        The MIME type of the file.
    size : int
        The size of the file in bytes.
    is_public : bool
        Whether the file is publicly accessible.
    created_at : datetime
        The timestamp when the file was uploaded.
    """
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="File name")
    content_type: str = Field(..., description="File MIME type")
    size: int = Field(..., description="File size in bytes")
    is_public: bool = Field(..., description="Whether the file is public")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        orm_mode = True


class FileProcessingRequest(BaseModel):
    """
    Request model for file processing.

    Attributes
    ----------
    directory_path : str
        Path to the directory containing files to process.
    recursive : bool
        Whether to process subdirectories (default is True).
    additional_metadata : Optional[Dict[str, Any]]
        Additional metadata to attach to all processed documents.
    """
    theme_id: str = Field(..., description="Theme ID to derive path from")
    recursive: bool = Field(True, description="Whether to process subdirectories")
    additional_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata to attach to documents")
    chunk_size: int = Field(1000, description="Size of each text chunk")
    chunk_overlap: int = Field(200, description="Number of overlapping characters per chunk")


class ProcessedFileSummary(BaseModel):
    """
    Summary of file processing results.

    Attributes
    ----------
    total_files : int
        Total number of files processed.
    successful : int
        Number of files successfully processed.
    unreadable : int
        Number of files that could not be read.
    language_detection_failures : int
        Number of files where language detection failed.
    files_with_warnings : int
        Number of files with warnings during processing.
    total_chunks_created
    chunks_vectorized
    """
    total_files: int
    successful: int
    unreadable: int
    language_detection_failures: int
    files_with_warnings: int
    total_chunks_created: int
    chunks_vectorized: int


class FileError(BaseModel):
    """
    Information about a file processing error.

    Attributes
    ----------
    filename : str
        The name of the file that caused the error.
    error : str
        A description of the error encountered.
    """
    filename: str
    error: str


class FileProcessingRecommendations(BaseModel):
    """
    Recommendations for processed files.

    Attributes
    ----------
    files_to_review : List[str]
        List of files that require manual review.
    files_to_consider_removing : List[str]
        List of files that may need to be removed.
    """
    files_to_review: List[str]
    files_to_consider_removing: List[str]


class FileProcessingReport(BaseModel):
    """
    Detailed report of file processing results.

    Attributes
    ----------
    summary : ProcessedFileSummary
        Summary of the file processing results.
    details : Dict[str, Any]
        Detailed information about each file's processing outcome.
    recommendations : FileProcessingRecommendations
        Recommendations based on the processing results.
    """
    summary: ProcessedFileSummary
    details: Dict[str, Any]
    recommendations: FileProcessingRecommendations
    detailed_successful_files: Optional[List['ProcessedFileDetails']] = None
    detailed_unreadable_files: Optional[List['UnreadableFileDetails']] = None
    detailed_language_detection_failures: Optional[List['LanguageFailureDetails']] = None
    detailed_files_with_warnings: Optional[List['FileWarningDetails']] = None
    chunking_stats: Optional['ChunkingStats'] = None
    vectorization_stats: Optional['VectorizationStats'] = None


class FileProcessingResponse(BaseModel):
    """
    Response model for file processing.

    Attributes
    ----------
    task_id : str
        Task ID associated with the processing.
    success : bool
        Indicates if the process succeeded or not.
    message : str
        Summary message.
    documents_count : int
        Number of documents successfully processed.
    report : FileProcessingReport
        Full detailed processing report.
    """
    task_id: str
    success: bool
    message: str
    documents_count: int
    report: FileProcessingReport
class VectorizationStats(BaseModel):
    """
    Statistics related to vectorization during file processing.

    Attributes
    ----------
    total_chunks_vectorized : int
        The total number of chunks successfully vectorized.
    embedding_batches : int
        The number of batches used for embedding generation.
    average_embedding_time_per_batch : Optional[float]
        The average time taken to process each embedding batch, if available.
    """
    total_chunks_vectorized: int
    embedding_batches: int
    average_embedding_time_per_batch: Optional[float]

class ChunkingStats(BaseModel):
    """
    Statistics related to text chunking during file processing.

    Attributes
    ----------
    total_chunks_created : int
        The total number of chunks created from all files.
    average_chunks_per_file : Optional[float]
        The average number of chunks created per file, if available.
    """
    total_chunks_created: int
    average_chunks_per_file: Optional[float]

class FileWarningDetails(BaseModel):
    """
    Details of a file with warnings during processing.

    Attributes
    ----------
    filename : str
        The name of the file.
    warnings : List[str]
        A list of warnings generated during the file's processing.
    """
    filename: str
    warnings: List[str]

class LanguageFailureDetails(BaseModel):
    """
    Details of a file where language detection failed.

    Attributes
    ----------
    filename : str
        The name of the file.
    error : str
        A description of the error encountered during language detection.
    """
    filename: str
    error: str

class UnreadableFileDetails(BaseModel):
    """
    Details of a file that could not be read.

    Attributes
    ----------
    filename : str
        The name of the unreadable file.
    error : str
        A description of the error encountered while reading the file.
    """
    filename: str
    error: str

class ProcessedFileDetails(BaseModel):
    """
    Details of a successfully processed file.

    Attributes
    ----------
    filename : str
        The name of the processed file.
    language : Optional[str]
        The detected language of the file, if available.
    metadata : Dict[str, Any]
        Additional metadata associated with the file.
    """
    filename: str
    language: Optional[str]
    metadata: Dict[str, Any]