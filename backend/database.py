"""
Supabase Database Client for Veritas Chatbot
Handles persistent storage of conversations
"""

import os
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
_supabase: Client | None = None

def get_supabase() -> Client | None:
    """Get or create Supabase client"""
    global _supabase
    
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    
    if not url or not key:
        return None
    
    if _supabase is None:
        try:
            _supabase = create_client(url, key)
        except Exception as e:
            print(f"Failed to connect to Supabase: {e}")
            return None
    
    return _supabase


def is_supabase_available() -> bool:
    """Check if Supabase is configured and available"""
    return get_supabase() is not None


# ========== CONVERSATIONS ==========

def save_conversation(conversation_id: str, title: str, messages: list) -> bool:
    """Save or update a conversation in Supabase"""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        data = {
            "id": conversation_id,
            "title": title,
            "messages": messages,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert (insert or update)
        supabase.table("conversations").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving conversation: {e}")
        return False


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation by ID"""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        result = supabase.table("conversations").select("*").eq("id", conversation_id).single().execute()
        return result.data
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return None


def get_all_conversations(limit: int = 50) -> list:
    """Get all conversations, ordered by most recent"""
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("conversations").select("id, title, updated_at").order("updated_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation"""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False


def clear_all_conversations() -> bool:
    """Delete all conversations"""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        # Delete all rows (Supabase requires a filter, so we use a workaround)
        supabase.table("conversations").delete().neq("id", "").execute()
        return True
    except Exception as e:
        print(f"Error clearing conversations: {e}")
        return False
