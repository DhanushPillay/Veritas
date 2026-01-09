"""
VERITAS - Audio Analysis
Uses Whisper for transcription + LLaMA for analysis
"""

import os
from groq import Groq

# Initialize client
client = Groq()


def transcribe_audio(filepath: str) -> dict:
    """
    Transcribe audio file using Whisper Large V3 Turbo.
    Returns detailed transcription with timestamps.
    """
    with open(filepath, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(filepath, file.read()),
            model="whisper-large-v3-turbo",
            temperature=0,
            response_format="verbose_json",
        )
    
    return {
        "text": transcription.text,
        "segments": getattr(transcription, 'segments', []),
        "language": getattr(transcription, 'language', 'unknown'),
        "duration": getattr(transcription, 'duration', 0)
    }


def analyze_audio(filepath: str, stream: bool = True) -> dict:
    """
    Complete audio analysis:
    1. Transcribe audio using Whisper
    2. Analyze transcription for authenticity using LLaMA
    """
    print("Step 1: Transcribing audio...")
    transcription = transcribe_audio(filepath)
    print(f"Transcription: {transcription['text'][:200]}...")
    
    print("\nStep 2: Analyzing for authenticity...")
    
    system_prompt = """You are Veritas, an audio forensics AI.
Analyze this audio transcription for:
- Voice cloning or synthesis patterns
- Unnatural speech rhythms
- AI-generated speech markers
- Content credibility and accuracy
- Emotional authenticity

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
            {"role": "user", "content": f"Analyze this audio transcription:\n\n{transcription['text']}"}
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
        return {"transcription": transcription, "analysis": result}
    else:
        return {
            "transcription": transcription,
            "analysis": completion.choices[0].message.content
        }


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # Default test file
        audio_file = os.path.join(os.path.dirname(__file__), "audio.m4a")
    
    if os.path.exists(audio_file):
        print(f"=== Audio Analysis: {audio_file} ===\n")
        result = analyze_audio(audio_file)
    else:
        print(f"File not found: {audio_file}")
        print("Usage: python audio_analysis.py <audio_file>")
