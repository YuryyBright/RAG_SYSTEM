# app/api/routes/documents.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from api.schemas.document import DocumentCreate, DocumentResponse
from domain.entities.document import Document

from domain.interfaces.embedding import EmbeddingInterface
from domain.interfaces.indexing import IndexInterface
from app.api.dependencies.dependencies import (
    get_document_repository,
    get_embedding_service,
    get_vector_index
)
from infrastructure.repositories.repository.document_repository import DocumentRepository

router = APIRouter()


@router.post("/", response_model=DocumentResponse)
async def create_document(
        document: DocumentCreate,
        document_repository: DocumentRepository = Depends(get_document_repository),
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        index_service: IndexInterface = Depends(get_vector_index)
):
    """
    Create a new document and index it.

    Parameters
    ----------
    document : DocumentCreate
        The document data to create.
    document_repository : DocumentRepository
        The document repository dependency.
    embedding_service : EmbeddingInterface
        The embedding service dependency.
    index_service : IndexInterface
        The indexing service dependency.

    Returns
    -------
    DocumentResponse
        The created document response.
    """
    # Create a document entity
    doc = Document(
        id="",  # Will be generated in store
        content=document.content,
        metadata=document.metadata
    )

    # Generate embeddings
    docs_with_embeddings = await embedding_service.embed_documents([doc])
    doc_with_embedding = docs_with_embeddings[0]

    # Save to database
    saved_doc = await document_repository.create_document(
        content=doc_with_embedding.content,
        embedding=doc_with_embedding.embedding,
        owner_id=doc_with_embedding.metadata.get("owner_id", "default_owner")
    )

    # Add to vector index
    await index_service.add_documents([saved_doc])

    return DocumentResponse(
        id=saved_doc.id,
        content=saved_doc.content,
        metadata=saved_doc.document_metadata,  # Changed to match DB model
        created_at=saved_doc.created_at,
        updated_at=saved_doc.updated_at
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
        document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    List all documents.

    Parameters
    ----------
    document_repository : DocumentRepository
        The document repository dependency.

    Returns
    -------
    List[DocumentResponse]
        A list of document responses.
    """
    documents = await document_repository.get_all()
    return [
        DocumentResponse(
            id=doc.id,
            content=doc.content,
            metadata=doc.document_metadata,  # Changed to match DB model
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
        document_id: str,
        document_repository: DocumentRepository = Depends(get_document_repository)
):
    """
    Get a document by ID.

    Parameters
    ----------
    document_id : str
        The ID of the document to retrieve.
    document_repository : DocumentRepository
        The document repository dependency.

    Returns
    -------
    DocumentResponse
        The retrieved document response.

    Raises
    ------
    HTTPException
        If the document is not found.
    """
    document = await document_repository.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        content=document.content,
        metadata=document.document_metadata,  # Changed to match DB model
        created_at=document.created_at,
        updated_at=document.updated_at
    )

#
# @router.delete("/{document_id}")
# async def delete_document(
#         document_id: str,
#         document_repository: DocumentRepository = Depends(get_document_repository),
#         index_service: IndexInterface = Depends(get_indexing_service)
# ):
#     """
#     Delete a document.
#
#     Parameters
#     ----------
#     document_id : str
#         The ID of the document to delete.
#     document_repository : DocumentRepository
#         The document repository dependency.
#     index_service : IndexInterface
#         The indexing service dependency.
#
#     Returns
#     -------
#     Dict[str, str]
#         A status message indicating the result of the deletion.
#
#     Raises
#     ------
#     HTTPException
#         If the document is not found.
#     """
#     deleted = await document_repository.delete_document(document_id)
#     if not deleted:
#         raise HTTPException(status_code=404, detail="Document not found")
#
#     await index_service.delete_document(document_id)
#
#     return {"status": "success", "message": f"Document {document_id} deleted"}
#
#
# async def process_document_upload(
#         directory: str,
#         document_loader: DocumentLoader,
#         embedding_service: EmbeddingInterface,
#         index_service: IndexInterface,
#         document_repository: DocumentRepository
# ):
#     """
#     Background task to process uploaded documents.
#
#     Parameters
#     ----------
#     directory : str
#         The directory containing the uploaded documents.
#     document_loader : DocumentLoader
#         The document loader dependency.
#     embedding_service : EmbeddingInterface
#         The embedding service dependency.
#     index_service : IndexInterface
#         The indexing service dependency.
#     document_repository : DocumentRepository
#         The document repository dependency.
#     """
#     documents = await document_loader.load_from_directory(directory, recursive=True)
#     documents_with_embeddings = await embedding_service.embed_documents(documents)
#
#     # Save documents to database
#     saved_documents = []
#     for doc in documents_with_embeddings:
#         saved_doc = await document_repository.create_document(
#             content=doc.content,
#             embedding=doc.embedding,
#             owner_id=doc.metadata.get("owner_id", "default_owner")
#         )
#         saved_documents.append(saved_doc)
#
#     # Add to vector index
#     await index_service.add_documents(saved_documents)
#
#     # Clean up
#     shutil.rmtree(directory, ignore_errors=True)
#
#
# @router.post("/upload")
# async def upload_documents(
#         background_tasks: BackgroundTasks,
#         files: List[UploadFile] = File(...),
#         metadata: Optional[str] = Form(None),
#         document_loader: DocumentLoader = Depends(get_document_loader),
#         embedding_service: EmbeddingInterface = Depends(get_embedding_service),
#         index_service: IndexInterface = Depends(get_indexing_service),
#         document_repository: DocumentRepository = Depends(get_document_repository)
# ):
#     """
#     Upload multiple document files and index them.
#
#     Parameters
#     ----------
#     background_tasks : BackgroundTasks
#         The background tasks dependency.
#     files : List[UploadFile]
#         The list of files to upload.
#     metadata : Optional[str]
#         Optional metadata for the documents.
#     document_loader : DocumentLoader
#         The document loader dependency.
#     embedding_service : EmbeddingInterface
#         The embedding service dependency.
#     index_service : IndexInterface
#         The indexing service dependency.
#     document_repository : DocumentRepository
#         The document repository dependency.
#
#     Returns
#     -------
#     Dict[str, str]
#         A status message indicating the result of the upload.
#
#     Raises
#     ------
#     HTTPException
#         If there is an error processing the upload.
#     """
#     temp_dir = tempfile.mkdtemp()
#
#     try:
#         meta_dict = {}
#         if metadata:
#             import json
#             meta_dict = json.loads(metadata)
#
#         for file in files:
#             file_path = os.path.join(temp_dir, file.filename)
#             with open(file_path, "wb") as f:
#                 shutil.copyfileobj(file.file, f)
#
#         background_tasks.add_task(
#             process_document_upload,
#             temp_dir,
#             document_loader,
#             embedding_service,
#             index_service,
#             document_repository
#         )
#
#         return {
#             "status": "processing",
#             "message": f"Processing {len(files)} files in the background"
#         }
#
#     except Exception as e:
#         shutil.rmtree(temp_dir, ignore_errors=True)
#         raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")