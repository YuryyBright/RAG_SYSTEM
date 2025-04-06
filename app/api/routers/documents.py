# app/api/routes/documents.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Dict, Optional
import os
import tempfile
import shutil
from app.schemas.document import DocumentCreate, DocumentResponse
from api.core.entities.document import Document
from app.infrastructure.database.document_store import DocumentStore
from app.infrastructure.loaders.document_loader import DocumentLoader
from api.core.interfaces.embedding import EmbeddingInterface
from api.core.interfaces.indexing import IndexInterface
from app.api.dependencies import (
    get_document_store,
    get_document_loader,
    get_embedding_service,
    get_indexing_service
)

router = APIRouter()


@router.post("/", response_model=DocumentResponse)
async def create_document(
        document: DocumentCreate,
        document_store: DocumentStore = Depends(get_document_store),
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        index_service: IndexInterface = Depends(get_indexing_service)
):
    """
    Create a new document and index it.

    Parameters
    ----------
    document : DocumentCreate
        The document data to create.
    document_store : DocumentStore
        The document store dependency.
    embedding_service : EmbeddingInterface
        The embedding service dependency.
    index_service : IndexInterface
        The indexing service dependency.

    Returns
    -------
    DocumentResponse
        The created document response.
    """
    doc = Document(
        id="",  # Will be generated in store
        content=document.content,
        metadata=document.metadata
    )

    docs_with_embeddings = await embedding_service.embed_documents([doc])
    doc_with_embedding = docs_with_embeddings[0]

    saved_doc = await document_store.save(doc_with_embedding)
    await index_service.add_documents([saved_doc])

    return DocumentResponse(
        id=saved_doc.id,
        content=saved_doc.content,
        metadata=saved_doc.metadata,
        created_at=saved_doc.created_at,
        updated_at=saved_doc.updated_at
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
        document_store: DocumentStore = Depends(get_document_store)
):
    """
    List all documents.

    Parameters
    ----------
    document_store : DocumentStore
        The document store dependency.

    Returns
    -------
    List[DocumentResponse]
        A list of document responses.
    """
    documents = await document_store.get_all()
    return [
        DocumentResponse(
            id=doc.id,
            content=doc.content,
            metadata=doc.metadata,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
        document_id: str,
        document_store: DocumentStore = Depends(get_document_store)
):
    """
    Get a document by ID.

    Parameters
    ----------
    document_id : str
        The ID of the document to retrieve.
    document_store : DocumentStore
        The document store dependency.

    Returns
    -------
    DocumentResponse
        The retrieved document response.

    Raises
    ------
    HTTPException
        If the document is not found.
    """
    document = await document_store.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        content=document.content,
        metadata=document.metadata,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.delete("/{document_id}")
async def delete_document(
        document_id: str,
        document_store: DocumentStore = Depends(get_document_store),
        index_service: IndexInterface = Depends(get_indexing_service)
):
    """
    Delete a document.

    Parameters
    ----------
    document_id : str
        The ID of the document to delete.
    document_store : DocumentStore
        The document store dependency.
    index_service : IndexInterface
        The indexing service dependency.

    Returns
    -------
    Dict[str, str]
        A status message indicating the result of the deletion.

    Raises
    ------
    HTTPException
        If the document is not found.
    """
    deleted = await document_store.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    await index_service.delete_document(document_id)

    return {"status": "success", "message": f"Document {document_id} deleted"}


async def process_document_upload(
        directory: str,
        document_loader: DocumentLoader,
        embedding_service: EmbeddingInterface,
        index_service: IndexInterface
):
    """
    Background task to process uploaded documents.

    Parameters
    ----------
    directory : str
        The directory containing the uploaded documents.
    document_loader : DocumentLoader
        The document loader dependency.
    embedding_service : EmbeddingInterface
        The embedding service dependency.
    index_service : IndexInterface
        The indexing service dependency.
    """
    documents = await document_loader.load_from_directory(directory, recursive=True)
    documents_with_embeddings = await embedding_service.embed_documents(documents)
    await index_service.add_documents(documents_with_embeddings)
    shutil.rmtree(directory, ignore_errors=True)


@router.post("/upload")
async def upload_documents(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        metadata: Optional[str] = Form(None),
        document_loader: DocumentLoader = Depends(get_document_loader),
        embedding_service: EmbeddingInterface = Depends(get_embedding_service),
        index_service: IndexInterface = Depends(get_indexing_service)
):
    """
    Upload multiple document files and index them.

    Parameters
    ----------
    background_tasks : BackgroundTasks
        The background tasks dependency.
    files : List[UploadFile]
        The list of files to upload.
    metadata : Optional[str]
        Optional metadata for the documents.
    document_loader : DocumentLoader
        The document loader dependency.
    embedding_service : EmbeddingInterface
        The embedding service dependency.
    index_service : IndexInterface
        The indexing service dependency.

    Returns
    -------
    Dict[str, str]
        A status message indicating the result of the upload.

    Raises
    ------
    HTTPException
        If there is an error processing the upload.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        meta_dict = {}
        if metadata:
            import json
            meta_dict = json.loads(metadata)

        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

        background_tasks.add_task(
            process_document_upload,
            temp_dir,
            document_loader,
            embedding_service,
            index_service
        )

        return {
            "status": "processing",
            "message": f"Processing {len(files)} files in the background"
        }

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")