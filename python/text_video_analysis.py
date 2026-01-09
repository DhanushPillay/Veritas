"""
VERITAS - Text & Video Analysis
Uses LLaMA 4 Scout for fact-checking and deepfake detection
"""

import os
from groq import Groq

# Initialize client (uses GROQ_API_KEY from environment)
client = Groq()

def analyze_text(text: str, stream: bool = True) -> str:
    """
    Analyze text for authenticity, misinformation, and AI generation markers.
    Returns a forensic analysis with verdict and confidence score.
    """
    system_prompt = """You are Veritas, a world-class fact-checking AI.
Analyze the provided text for:
- Factual accuracy and claims
- AI-generated content patterns (LLM markers)
- Logical consistency and coherence
- Potential misinformation or bias
- Credibility score

Respond with JSON:
{
    "verdict": "Authentic" | "Fake/Generated" | "Inconclusive" | "Suspicious",
    "confidence": 0-100,
    "summary": "...",
    "reasoning": ["..."],
    "technicalDetails": [{"label": "...", "value": "...", "status": "pass|fail|warn", "explanation": "..."}]
}"""

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"}
        ],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=stream,
        stop=None
    )

    if stream:
        result = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")
            result += content
        print()  # New line after streaming
        return result
    else:
        return completion.choices[0].message.content


def analyze_video_description(video_info: dict, stream: bool = True) -> str:
    """
    Analyze video for deepfake indicators based on description.
    video_info should contain: name, size, duration, etc.
    """
    system_prompt = """You are Veritas, a deepfake detection AI.
Analyze the video for:
- Face manipulation and deepfake indicators
- Lip sync accuracy with audio
- Temporal consistency between frames
- Compression artifacts suggesting editing
- Audio-visual synchronization

Respond with JSON:
{
    "verdict": "Authentic" | "Fake/Generated" | "Inconclusive" | "Suspicious",
    "confidence": 0-100,
    "summary": "...",
    "reasoning": ["..."],
    "technicalDetails": [{"label": "...", "value": "...", "status": "pass|fail|warn", "explanation": "..."}]
}"""

    user_message = f"""Perform deepfake detection on this video:
File: {video_info.get('name', 'unknown')}
Size: {video_info.get('size', 'unknown')}
Duration: {video_info.get('duration', 'unknown')}
"""

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=stream,
        stop=None
    )

    if stream:
        result = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")
            result += content
        print()
        return result
    else:
        return completion.choices[0].message.content


# Example usage
if __name__ == "__main__":
    # Test text analysis
    sample_text = """
    Breaking news: Scientists discover that drinking coffee can increase 
    lifespan by 50 years according to a new study published yesterday.
    """
    
    print("=== Text Analysis ===")
    result = analyze_text(sample_text)
