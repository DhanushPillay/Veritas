"""
VERITAS - AI Text Detection Module
Detects if text was written by AI or human using trained DistilBERT model
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Model path (relative to project root)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
MODEL_PATH = os.path.join(PROJECT_ROOT, "veritas_text_detector")

# Global model and tokenizer (loaded once)
_model = None
_tokenizer = None
_device = None


def load_model():
    """Load the trained text detection model (lazy loading)"""
    global _model, _tokenizer, _device
    
    if _model is not None:
        return _model, _tokenizer, _device
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Text detection model not found at {MODEL_PATH}")
    
    print(f"📥 Loading text detection model from {MODEL_PATH}...")
    
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    _model.to(_device)
    _model.eval()
    
    print(f"✅ Text detection model loaded on {_device}")
    return _model, _tokenizer, _device


def detect_ai_text(text: str, max_length: int = 256) -> dict:
    """
    Detect if text is AI-generated or human-written.
    
    Args:
        text: The text to analyze
        max_length: Maximum token length (default 256)
    
    Returns:
        dict with:
            - is_ai: bool - True if AI-generated
            - confidence: float - Confidence percentage (0-100)
            - label: str - "ai_generated" or "human"
            - probabilities: dict - Raw probabilities for each class
    """
    try:
        model, tokenizer, device = load_model()
        
        # Tokenize input
        inputs = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)[0]
        
        # Get prediction
        # Label 0 = human, Label 1 = ai_generated
        human_prob = probabilities[0].item() * 100
        ai_prob = probabilities[1].item() * 100
        
        is_ai = ai_prob > human_prob
        confidence = max(human_prob, ai_prob)
        label = "ai_generated" if is_ai else "human"
        
        return {
            "is_ai": is_ai,
            "confidence": round(confidence, 2),
            "label": label,
            "probabilities": {
                "human": round(human_prob, 2),
                "ai_generated": round(ai_prob, 2)
            }
        }
        
    except FileNotFoundError as e:
        return {
            "error": str(e),
            "is_ai": None,
            "confidence": 0,
            "label": "unknown"
        }
    except Exception as e:
        return {
            "error": f"Detection failed: {str(e)}",
            "is_ai": None,
            "confidence": 0,
            "label": "unknown"
        }


def is_model_available() -> bool:
    """Check if the text detection model is available"""
    return os.path.exists(MODEL_PATH)
