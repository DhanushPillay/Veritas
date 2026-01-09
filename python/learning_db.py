"""
VERITAS - Learning Database
Stores learned patterns for future analysis improvement
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Path to patterns database
DB_PATH = os.path.join(os.path.dirname(__file__), 'patterns.json')


def load_patterns() -> Dict:
    """Load patterns from JSON file"""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"patterns": [], "stats": {"total_learned": 0, "last_updated": None}}


def save_patterns(data: Dict) -> None:
    """Save patterns to JSON file"""
    data["stats"]["last_updated"] = datetime.now().isoformat()
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_pattern(
    media_type: str,
    pattern_description: str,
    correct_verdict: str,
    confidence: int = 90,
    original_verdict: str = None,
    example_content: str = None
) -> Dict:
    """
    Add a new learned pattern to the database.
    
    Args:
        media_type: text, image, video, or audio
        pattern_description: What to look for (e.g., "6 fingers on hands")
        correct_verdict: The correct verdict for this pattern
        confidence: How confident this pattern is (0-100)
        original_verdict: What the AI originally predicted (for learning)
        example_content: Optional example that triggered this learning
    
    Returns:
        The created pattern object
    """
    data = load_patterns()
    
    pattern = {
        "id": str(uuid.uuid4()),
        "type": media_type,
        "pattern": pattern_description,
        "verdict": correct_verdict,
        "confidence": confidence,
        "original_verdict": original_verdict,
        "example": example_content[:200] if example_content else None,  # Truncate
        "created": datetime.now().isoformat(),
        "usage_count": 0,
        "effectiveness": None  # Track if this pattern helps
    }
    
    data["patterns"].append(pattern)
    data["stats"]["total_learned"] += 1
    save_patterns(data)
    
    return pattern


def get_patterns_by_type(media_type: str, limit: int = 10) -> List[Dict]:
    """
    Get learned patterns for a specific media type.
    Returns most relevant patterns first (by usage + recency).
    """
    data = load_patterns()
    
    # Filter by type
    type_patterns = [p for p in data["patterns"] if p["type"] == media_type]
    
    # Sort by usage count (descending) then by date (newest first)
    type_patterns.sort(key=lambda x: (x.get("usage_count", 0), x["created"]), reverse=True)
    
    return type_patterns[:limit]


def get_all_patterns() -> List[Dict]:
    """Get all learned patterns"""
    return load_patterns()["patterns"]


def increment_usage(pattern_id: str) -> None:
    """Mark a pattern as used in an analysis"""
    data = load_patterns()
    
    for pattern in data["patterns"]:
        if pattern["id"] == pattern_id:
            pattern["usage_count"] = pattern.get("usage_count", 0) + 1
            break
    
    save_patterns(data)


def update_effectiveness(pattern_id: str, was_helpful: bool) -> None:
    """Track if a pattern helped with correct detection"""
    data = load_patterns()
    
    for pattern in data["patterns"]:
        if pattern["id"] == pattern_id:
            if pattern.get("effectiveness") is None:
                pattern["effectiveness"] = {"helpful": 0, "not_helpful": 0}
            
            if was_helpful:
                pattern["effectiveness"]["helpful"] += 1
            else:
                pattern["effectiveness"]["not_helpful"] += 1
            break
    
    save_patterns(data)


def delete_pattern(pattern_id: str) -> bool:
    """Delete a pattern by ID"""
    data = load_patterns()
    original_len = len(data["patterns"])
    data["patterns"] = [p for p in data["patterns"] if p["id"] != pattern_id]
    
    if len(data["patterns"]) < original_len:
        save_patterns(data)
        return True
    return False


def format_patterns_for_prompt(patterns: List[Dict]) -> str:
    """
    Format learned patterns as few-shot examples for the system prompt.
    """
    if not patterns:
        return ""
    
    lines = ["### LEARNED PATTERNS FROM USER FEEDBACK:"]
    lines.append("Apply these patterns when analyzing media:\n")
    
    for i, p in enumerate(patterns, 1):
        lines.append(f"{i}. **Pattern**: \"{p['pattern']}\"")
        lines.append(f"   → Verdict: {p['verdict']} ({p['confidence']}% confidence)")
        if p.get("example"):
            lines.append(f"   Example: \"{p['example'][:50]}...\"")
        lines.append("")
    
    return "\n".join(lines)


def get_stats() -> Dict:
    """Get learning statistics"""
    data = load_patterns()
    patterns = data["patterns"]
    
    return {
        "total_patterns": len(patterns),
        "by_type": {
            "text": len([p for p in patterns if p["type"] == "text"]),
            "image": len([p for p in patterns if p["type"] == "image"]),
            "video": len([p for p in patterns if p["type"] == "video"]),
            "audio": len([p for p in patterns if p["type"] == "audio"])
        },
        "total_usage": sum(p.get("usage_count", 0) for p in patterns),
        "last_updated": data["stats"].get("last_updated")
    }


# Initialize empty database if it doesn't exist
if not os.path.exists(DB_PATH):
    save_patterns({"patterns": [], "stats": {"total_learned": 0, "last_updated": None}})
