"""
Supabase Client Module
Handles all Supabase operations for:
- Analysis history (database)
- Media uploads (storage)
"""

import os
import uuid
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = None

def get_client() -> Client:
    """Get or create Supabase client instance."""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


# ========== STORAGE OPERATIONS ==========

BUCKET_NAME = "media-uploads"

def upload_media(file_bytes: bytes, filename: str, content_type: str = None) -> str:
    """
    Upload media file to Supabase Storage.
    
    Args:
        file_bytes: Raw file bytes
        filename: Original filename
        content_type: MIME type (optional)
    
    Returns:
        Public URL of the uploaded file
    """
    client = get_client()
    
    # Generate unique filename to prevent collisions
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else f"{uuid.uuid4().hex}"
    file_path = f"uploads/{unique_name}"
    
    # Upload to storage
    options = {}
    if content_type:
        options["content-type"] = content_type
    
    client.storage.from_(BUCKET_NAME).upload(
        path=file_path,
        file=file_bytes,
        file_options=options
    )
    
    # Get public URL
    public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)
    return public_url


def delete_media(file_url: str) -> bool:
    """
    Delete media file from Supabase Storage.
    
    Args:
        file_url: Public URL of the file
    
    Returns:
        True if deleted successfully
    """
    if not file_url:
        return True
    
    client = get_client()
    
    # Extract file path from URL
    # URL format: https://<project>.supabase.co/storage/v1/object/public/<bucket>/<path>
    try:
        path_start = file_url.find(f"/storage/v1/object/public/{BUCKET_NAME}/")
        if path_start == -1:
            return False
        file_path = file_url[path_start + len(f"/storage/v1/object/public/{BUCKET_NAME}/"):]
        
        client.storage.from_(BUCKET_NAME).remove([file_path])
        return True
    except Exception as e:
        print(f"Error deleting media: {e}")
        return False


# ========== DATABASE OPERATIONS ==========

TABLE_NAME = "analysis_history"

def save_analysis(record: dict) -> dict:
    """
    Save analysis result to database.
    
    Args:
        record: Dictionary containing:
            - type: 'text', 'image', 'video', 'audio'
            - preview: First 60 chars or filename
            - media_url: Supabase Storage URL (optional)
            - thumbnail_url: Thumbnail URL (optional)
            - result: Full analysis result object
            - verdict: 'Authentic', 'Fake/Generated', etc.
            - confidence: 0-100
    
    Returns:
        Inserted record with ID
    """
    client = get_client()
    
    data = {
        "type": record.get("type"),
        "preview": record.get("preview", "")[:200],  # Limit preview length
        "media_url": record.get("media_url"),
        "thumbnail_url": record.get("thumbnail_url"),
        "result": record.get("result", {}),
        "verdict": record.get("verdict"),
        "confidence": record.get("confidence", 0)
    }
    
    response = client.table(TABLE_NAME).insert(data).execute()
    return response.data[0] if response.data else None


def get_history(limit: int = 20) -> list:
    """
    Get recent analysis history.
    
    Args:
        limit: Maximum number of records to return
    
    Returns:
        List of analysis records, newest first
    """
    client = get_client()
    
    response = client.table(TABLE_NAME)\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    
    return response.data or []


def get_analysis(record_id: str) -> dict:
    """
    Get a single analysis record by ID.
    
    Args:
        record_id: UUID of the record
    
    Returns:
        Analysis record or None
    """
    client = get_client()
    
    response = client.table(TABLE_NAME)\
        .select("*")\
        .eq("id", record_id)\
        .single()\
        .execute()
    
    return response.data


def delete_analysis(record_id: str) -> bool:
    """
    Delete an analysis record and its associated media.
    
    Args:
        record_id: UUID of the record to delete
    
    Returns:
        True if deleted successfully
    """
    client = get_client()
    
    # First, get the record to find media URLs
    record = get_analysis(record_id)
    if not record:
        return False
    
    # Delete associated media files
    if record.get("media_url"):
        delete_media(record["media_url"])
    if record.get("thumbnail_url"):
        delete_media(record["thumbnail_url"])
    
    # Delete the database record
    client.table(TABLE_NAME).delete().eq("id", record_id).execute()
    return True
