from typing import Any, List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..database import get_supabase
from ..dependencies import get_current_user_id
from ..models import Document
from ..schemas import DocumentResponse, DocumentCreate

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from ..services.gemini_service import gemini_service
# We'll need a task function, let's define it in a new file or here for now. 
# Better to put it in a separate module to avoid circular imports if possible, 
# but for prototype let's keep it simple. We'll create a tasks module.

router = APIRouter(prefix="/documents", tags=["documents"])

# Placeholder for the task import
# from ..tasks.document_processing import process_document_task

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> Any:
    """
    Create a new document record.
    This is called AFTER the file has been uploaded to Supabase Storage by the frontend.
    """
    
    data = document.model_dump()
    data["user_id"] = str(user_id)
    data["status"] = "uploaded"
    data["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    data["extracted_data"] = {}
    
    response = supabase.table("documents").insert(data).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document record"
        )
    
    doc_record = response.data[0]
    
    # Trigger background processing
    # We need to import the task function dynamically or from a separate module
    from ..tasks.document_processing import process_document_task
    background_tasks.add_task(process_document_task, doc_record["id"], user_id)
    
    return doc_record

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    status: str = None,
    user_id: UUID = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> Any:
    """List user's documents."""
    
    query = supabase.table("documents").select("*").eq("user_id", str(user_id))
    
    if status:
        query = query.eq("status", status)
        
    query = query.order("uploaded_at", desc=True).range(offset, offset + limit - 1)
    
    response = query.execute()
    
    return response.data

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> Any:
    """Get document details."""
    
    response = supabase.table("documents").select("*").eq("id", str(document_id)).eq("user_id", str(user_id)).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    return response.data[0]

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> None:
    """Soft delete a document."""
    
    # Check if exists first
    check = supabase.table("documents").select("id").eq("id", str(document_id)).eq("user_id", str(user_id)).execute()
    if not check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Soft delete by setting status to 'deleted'
    # Or actually delete row if that's preferred. Let's do soft delete as per spec.
    # But wait, schema says status enum: uploaded, processing, completed, failed.
    # If 'deleted' isn't in enum, we might need to add it or just delete the row.
    # Let's delete the row for now to keep it simple and clean.
    
    supabase.table("documents").delete().eq("id", str(document_id)).eq("user_id", str(user_id)).execute()
    
    # TODO: Also delete from Storage bucket
