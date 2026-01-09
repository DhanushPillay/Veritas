"""
VERITAS - Supabase Cloud Database
Cloud storage for learned patterns with real-time sync
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Get credentials from environment
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

# Initialize client
_client: Optional[Client] = None


def get_client() -> Client:
    """Get or create Supabase client"""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def load_patterns() -> Dict:
    """Load all patterns from Supabase"""
    try:
        client = get_client()
        response = client.table('patterns').select('*').execute()
        return {"patterns": response.data or [], "stats": get_stats()}
    except Exception as e:
        print(f"Supabase load error: {e}")
        return {"patterns": [], "stats": {"total_learned": 0}}


def save_patterns(data: Dict) -> None:
    """Not needed for Supabase - each operation saves individually"""
    pass


def add_pattern(
    media_type: str,
    pattern_description: str,
    correct_verdict: str,
    confidence: int = 90,
    original_verdict: str = None,
    example_content: str = None
) -> Dict:
    """Add a new learned pattern to cloud database"""
    try:
        client = get_client()
        
        pattern = {
            "type": media_type,
            "pattern": pattern_description,
            "verdict": correct_verdict,
            "confidence": confidence,
            "original_verdict": original_verdict,
            "example": example_content[:200] if example_content else None,
            "usage_count": 0
        }
        
        response = client.table('patterns').insert(pattern).execute()
        
        if response.data:
            return response.data[0]
        return pattern
        
    except Exception as e:
        print(f"Supabase add error: {e}")
        return {"error": str(e)}


def get_patterns_by_type(media_type: str, limit: int = 10) -> List[Dict]:
    """Get learned patterns for a specific media type"""
    try:
        client = get_client()
        response = (client.table('patterns')
                   .select('*')
                   .eq('type', media_type)
                   .order('usage_count', desc=True)
                   .limit(limit)
                   .execute())
        return response.data or []
    except Exception as e:
        print(f"Supabase query error: {e}")
        return []


def get_all_patterns() -> List[Dict]:
    """Get all learned patterns"""
    return load_patterns()["patterns"]


def increment_usage(pattern_id: str) -> None:
    """Mark a pattern as used in an analysis"""
    try:
        client = get_client()
        # Get current count
        response = client.table('patterns').select('usage_count').eq('id', pattern_id).execute()
        if response.data:
            current = response.data[0].get('usage_count', 0)
            client.table('patterns').update({'usage_count': current + 1}).eq('id', pattern_id).execute()
    except Exception as e:
        print(f"Supabase increment error: {e}")


def update_effectiveness(pattern_id: str, was_helpful: bool) -> None:
    """Track if a pattern helped with correct detection"""
    try:
        client = get_client()
        response = client.table('patterns').select('effectiveness').eq('id', pattern_id).execute()
        
        if response.data:
            effectiveness = response.data[0].get('effectiveness') or {"helpful": 0, "not_helpful": 0}
            if was_helpful:
                effectiveness["helpful"] += 1
            else:
                effectiveness["not_helpful"] += 1
            
            client.table('patterns').update({'effectiveness': effectiveness}).eq('id', pattern_id).execute()
    except Exception as e:
        print(f"Supabase effectiveness error: {e}")


def delete_pattern(pattern_id: str) -> bool:
    """Delete a pattern by ID"""
    try:
        client = get_client()
        client.table('patterns').delete().eq('id', pattern_id).execute()
        return True
    except Exception as e:
        print(f"Supabase delete error: {e}")
        return False


def format_patterns_for_prompt(patterns: List[Dict]) -> str:
    """Format learned patterns as few-shot examples for the system prompt"""
    if not patterns:
        return ""
    
    lines = ["### LEARNED PATTERNS FROM USER FEEDBACK:"]
    lines.append("Apply these patterns when analyzing media:\n")
    
    for i, p in enumerate(patterns, 1):
        lines.append(f"{i}. **Pattern**: \"{p.get('pattern', '')}\"")
        lines.append(f"   → Verdict: {p.get('verdict', '')} ({p.get('confidence', 90)}% confidence)")
        if p.get("example"):
            lines.append(f"   Example: \"{p['example'][:50]}...\"")
        lines.append("")
    
    return "\n".join(lines)


def get_stats() -> Dict:
    """Get learning statistics from cloud database"""
    try:
        client = get_client()
        response = client.table('patterns').select('type, usage_count').execute()
        patterns = response.data or []
        
        return {
            "total_patterns": len(patterns),
            "by_type": {
                "text": len([p for p in patterns if p.get("type") == "text"]),
                "image": len([p for p in patterns if p.get("type") == "image"]),
                "video": len([p for p in patterns if p.get("type") == "video"]),
                "audio": len([p for p in patterns if p.get("type") == "audio"])
            },
            "total_usage": sum(p.get("usage_count", 0) for p in patterns),
            "storage": "supabase_cloud"
        }
    except Exception as e:
        print(f"Supabase stats error: {e}")
        return {"total_patterns": 0, "storage": "error", "error": str(e)}
