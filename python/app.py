"""
VERITAS - Flask Backend API
Connects the web frontend with Groq AI models
With Pattern Learning System
"""

import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

# Import learning database and fact-check service
import learning_db
from factcheck_service import FactCheckService, search_news_for_claim

# Initialize fact-check service
factcheck = FactCheckService()

app = Flask(__name__)
CORS(app)

# Initialize Groq client
client = None

def get_client():
    global client
    if client is None:
        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        client = Groq(api_key=api_key)
    return client


# System prompts for different media types
PROMPTS = {
    'text': """You are Veritas, a fact-checking AI. Analyze for:
- Factual accuracy and claims
- AI-generated content patterns
- Logical consistency
- Misinformation or bias
- Credibility score""",

    'image': """You are Veritas, an image forensics AI. Analyze for:
- AI generation artifacts (Midjourney, DALL-E, Stable Diffusion)
- Manipulation signs
- Lighting/shadow consistency
- Anatomical anomalies""",

    'video': """You are Veritas, a deepfake detection AI. Analyze for:
- Face manipulation indicators
- Lip sync accuracy
- Temporal consistency
- Compression artifacts
- Audio-visual sync""",

    'audio': """You are Veritas, an audio forensics AI. Analyze for:
- Voice cloning patterns
- Unnatural speech rhythms
- AI speech markers
- Content credibility"""
}

RESPONSE_FORMAT = """
Respond with ONLY valid JSON:
{
    "verdict": "Authentic" | "Fake/Generated" | "Inconclusive" | "Suspicious",
    "confidence": 0-100,
    "summary": "...",
    "reasoning": ["..."],
    "technicalDetails": [{"label": "...", "value": "...", "status": "pass|fail|warn", "explanation": "..."}]
}"""


def build_prompt_with_patterns(media_type: str) -> str:
    """Build system prompt with learned patterns injected"""
    base_prompt = PROMPTS.get(media_type, PROMPTS['text'])
    
    # Get learned patterns for this type
    patterns = learning_db.get_patterns_by_type(media_type, limit=5)
    pattern_text = learning_db.format_patterns_for_prompt(patterns)
    
    if pattern_text:
        return f"{base_prompt}\n\n{pattern_text}\n{RESPONSE_FORMAT}"
    
    return f"{base_prompt}{RESPONSE_FORMAT}"


# ========== HEALTH & STATS ==========

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    stats = learning_db.get_stats()
    return jsonify({
        "status": "ok",
        "message": "Veritas API is running",
        "learning": stats
    })


# ========== LEARNING ENDPOINTS ==========

@app.route('/api/learn', methods=['POST'])
def learn_pattern():
    """Learn a new pattern from user feedback"""
    try:
        data = request.json
        
        pattern = learning_db.add_pattern(
            media_type=data.get('type', 'text'),
            pattern_description=data.get('pattern', ''),
            correct_verdict=data.get('verdict', 'Suspicious'),
            confidence=data.get('confidence', 90),
            original_verdict=data.get('originalVerdict'),
            example_content=data.get('example')
        )
        
        return jsonify({
            "success": True,
            "message": "Pattern learned successfully",
            "pattern": pattern
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/patterns', methods=['GET'])
def get_patterns():
    """Get all learned patterns"""
    media_type = request.args.get('type')
    
    if media_type:
        patterns = learning_db.get_patterns_by_type(media_type)
    else:
        patterns = learning_db.get_all_patterns()
    
    return jsonify({"patterns": patterns, "stats": learning_db.get_stats()})


@app.route('/api/patterns/<pattern_id>', methods=['DELETE'])
def delete_pattern(pattern_id):
    """Delete a learned pattern"""
    if learning_db.delete_pattern(pattern_id):
        return jsonify({"success": True})
    return jsonify({"error": "Pattern not found"}), 404


# ========== VERIFICATION ENDPOINTS ==========

@app.route('/api/verify/text', methods=['POST'])
def verify_text():
    """Analyze text for authenticity with fact-check cross-reference"""
    try:
        data = request.json
        text = data.get('text', '')
        use_factcheck = data.get('useSearch', False)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Step 1: Search fact-check databases (if enabled)
        factcheck_results = []
        factcheck_boost = {"modifier": 0, "summary": ""}
        news_results = []
        
        if use_factcheck:
            factcheck_results = factcheck.search_claims(text[:200])
            factcheck_boost = factcheck.get_credibility_boost(factcheck_results)
            news_results = search_news_for_claim(text[:100])
        
        # Step 2: Build enhanced prompt with fact-check context
        groq = get_client()
        system_prompt = build_prompt_with_patterns('text')
        
        user_content = f"Fact-check this text:\n\n{text}"
        
        if factcheck_results:
            user_content += f"\n\n### FACT-CHECK DATABASE RESULTS:\n"
            for fc in factcheck_results[:3]:
                user_content += f"- Claim: '{fc['claim'][:100]}' rated '{fc['rating']}' by {fc['publisher']}\n"
        
        completion = groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=1,
            max_tokens=1024
        )
        
        response_text = completion.choices[0].message.content
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
            
            # Add fact-check sources to result
            if factcheck_results:
                result['sources'] = result.get('sources', [])
                result['sources'].extend([{
                    'title': f"{fc['publisher']}: {fc['rating']}",
                    'uri': fc['url']
                } for fc in factcheck_results])
                result['factCheckSummary'] = factcheck_boost['summary']
            
            if news_results:
                result['relatedNews'] = news_results
            
            return jsonify(result)
        
        return jsonify({"error": "Invalid AI response"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/verify/image', methods=['POST'])
def verify_image():
    """Analyze image for AI generation/manipulation"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        file_content = file.read()
        
        groq = get_client()
        system_prompt = build_prompt_with_patterns('image')
        
        completion = groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze image: {file.filename}, Type: {file.content_type}, Size: {len(file_content)} bytes"}
            ],
            temperature=1,
            max_tokens=1024
        )
        
        response_text = completion.choices[0].message.content
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end > start:
            return jsonify(json.loads(response_text[start:end]))
        
        return jsonify({"error": "Invalid AI response"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/verify/video', methods=['POST'])
def verify_video():
    """Analyze video for deepfakes"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        groq = get_client()
        system_prompt = build_prompt_with_patterns('video')
        
        completion = groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Deepfake analysis for: {file.filename}, Type: {file.content_type}"}
            ],
            temperature=1,
            max_tokens=1024
        )
        
        response_text = completion.choices[0].message.content
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end > start:
            return jsonify(json.loads(response_text[start:end]))
        
        return jsonify({"error": "Invalid AI response"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/verify/audio', methods=['POST'])
def verify_audio():
    """Transcribe and analyze audio"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        groq = get_client()
        
        # Save to temp file for Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Step 1: Transcribe with Whisper
            with open(tmp_path, 'rb') as audio_file:
                transcription = groq.audio.transcriptions.create(
                    file=(file.filename, audio_file.read()),
                    model="whisper-large-v3-turbo",
                    temperature=0,
                    response_format="verbose_json"
                )
            
            transcript_text = transcription.text
            
            # Step 2: Analyze with learned patterns
            system_prompt = build_prompt_with_patterns('audio')
            
            completion = groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this audio transcription:\n\n{transcript_text}"}
                ],
                temperature=1,
                max_tokens=1024
            )
            
            response_text = completion.choices[0].message.content
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end > start:
                result = json.loads(response_text[start:end])
                result['transcription'] = transcript_text
                return jsonify(result)
            
            return jsonify({"error": "Invalid AI response"}), 500
            
        finally:
            os.unlink(tmp_path)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("VERITAS Backend API with Learning System")
    print("=" * 50)
    stats = learning_db.get_stats()
    print(f"Learned patterns: {stats['total_patterns']}")
    print(f"Make sure GROQ_API_KEY is set!")
    print("Starting server on http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
