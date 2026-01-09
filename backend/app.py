"""
VERITAS - Flask Backend API
Clean, modular API server
"""

import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

from config import Config
from learning.supabase_db import (
    load_patterns, get_patterns_by_type, add_pattern, 
    format_patterns_for_prompt, get_stats, delete_pattern
)
from external.factcheck import FactCheckService, search_news_for_claim
from forensics.image_forensics import analyze_image_bytes
from forensics.reverse_search import search_image

# Initialize
Config.validate()
app = Flask(__name__)
CORS(app)

# Configure max upload size to 2GB
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# Groq client
client = None

def get_client():
    global client
    if client is None:
        client = Groq(api_key=Config.GROQ_API_KEY)
    return client

# System prompts
PROMPTS = {
    'text': """You are Veritas, a fact-checking AI. Analyze for:
- Factual accuracy and claims
- AI-generated content patterns
- Logical consistency
- Misinformation or bias""",
    
    'image': """You are Veritas, an image forensics AI. Analyze for:
- AI generation artifacts
- Manipulation signs
- Lighting/shadow consistency
- Anatomical anomalies""",
    
    'video': """You are Veritas, a deepfake detection AI. Analyze for:
- Face manipulation indicators
- Lip sync accuracy
- Temporal consistency""",
    
    'audio': """You are Veritas, an audio forensics AI. Analyze for:
- Voice cloning patterns
- Unnatural speech rhythms
- AI speech markers"""
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

factcheck = FactCheckService()


def build_prompt_with_patterns(media_type):
    """Build AI prompt with learned patterns, return prompt and pattern info"""
    base = PROMPTS.get(media_type, PROMPTS['text'])
    patterns = get_patterns_by_type(media_type, limit=5)
    pattern_text = format_patterns_for_prompt(patterns)
    
    # Return tuple: (prompt, patterns_used)
    patterns_info = [{"pattern": p.get("pattern", ""), "verdict": p.get("verdict", "")} for p in patterns]
    
    if pattern_text:
        return f"{base}\n\n{pattern_text}\n{RESPONSE_FORMAT}", patterns_info
    return f"{base}{RESPONSE_FORMAT}", patterns_info


# ========== HEALTH ==========

@app.route('/api/health', methods=['GET'])
def health():
    stats = get_stats()
    return jsonify({"status": "ok", "learning": stats})


# ========== LEARNING ==========

@app.route('/api/learn', methods=['POST'])
def learn_pattern():
    try:
        data = request.json
        pattern = add_pattern(
            media_type=data.get('type', 'text'),
            pattern_description=data.get('pattern', ''),
            correct_verdict=data.get('verdict', 'Suspicious'),
            confidence=data.get('confidence', 90),
            original_verdict=data.get('originalVerdict'),
            example_content=data.get('example')
        )
        return jsonify({"success": True, "pattern": pattern})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/patterns', methods=['GET'])
def get_patterns_endpoint():
    media_type = request.args.get('type')
    if media_type:
        patterns = get_patterns_by_type(media_type)
    else:
        patterns = load_patterns()["patterns"]
    return jsonify({"patterns": patterns, "stats": get_stats()})


@app.route('/api/patterns/<pattern_id>', methods=['DELETE'])
def delete_pattern_endpoint(pattern_id):
    if delete_pattern(pattern_id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


# ========== TEXT VERIFICATION ==========

@app.route('/api/verify/text', methods=['POST'])
def verify_text():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    try:
        start_time = time.time()
        data = request.json
        text = data.get('text', '')
        use_search = data.get('useSearch', False)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        groq = get_client()
        system_prompt, patterns_used = build_prompt_with_patterns('text')
        
        def run_ai(prompt):
            completion = groq.chat.completions.create(
                model=Config.TEXT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=1, max_tokens=1024
            )
            return completion.choices[0].message.content
        
        base_prompt = f"Fact-check this text:\n\n{text}"
        
        factcheck_results = []
        news_results = []
        
        if use_search:
            with ThreadPoolExecutor(max_workers=3) as ex:
                futures = {
                    ex.submit(run_ai, base_prompt): "ai",
                    ex.submit(factcheck.search_claims, text[:200]): "fc",
                    ex.submit(search_news_for_claim, text[:100]): "news"
                }
                for f in as_completed(futures):
                    name = futures[f]
                    try:
                        if name == "ai": ai_response = f.result()
                        elif name == "fc": factcheck_results = f.result()
                        elif name == "news": news_results = f.result()
                    except: pass
        else:
            ai_response = run_ai(base_prompt)
        
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        
        if start != -1 and end > start:
            result = json.loads(ai_response[start:end])
            if factcheck_results:
                boost = factcheck.get_credibility_boost(factcheck_results)
                result['sources'] = [{'title': f"{fc['publisher']}: {fc['rating']}", 'uri': fc['url']} for fc in factcheck_results]
                result['factCheckSummary'] = boost['summary']
            if news_results:
                result['relatedNews'] = news_results
            result['processingTime'] = f"{time.time() - start_time:.2f}s"
            result['learnedPatternsUsed'] = len(patterns_used)
            result['patternsApplied'] = patterns_used
            return jsonify(result)
        
        return jsonify({"error": "Invalid response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== IMAGE VERIFICATION ==========

@app.route('/api/verify/image', methods=['POST'])
def verify_image():
    """Analyze image with forensics-informed AI analysis"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    try:
        start_time = time.time()
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
        
        file = request.files['file']
        content = file.read()
        filename = file.filename
        
        groq = get_client()
        
        # Step 1: Run forensics FIRST to get actual evidence
        with ThreadPoolExecutor(max_workers=2) as ex:
            forensics_future = ex.submit(analyze_image_bytes, content, filename)
            reverse_future = ex.submit(search_image, content)
            
            forensics = forensics_future.result()
            reverse = reverse_future.result()
        
        # Step 2: Build AI prompt with forensic evidence
        ela = forensics.get("ela", {})
        metadata = forensics.get("metadata", {})
        indicators = forensics.get("manipulation_indicators", [])
        risk_score = forensics.get("risk_score", 0)
        
        forensic_evidence = f"""
FORENSIC ANALYSIS RESULTS:
- ELA Max Error: {ela.get('max_error', 0)}% (>30% suggests manipulation)
- ELA Suspicious Regions: {ela.get('suspicious_regions', 0)}%
- Has EXIF Metadata: {metadata.get('has_metadata', False)}
- Camera: {metadata.get('camera', {}).get('Model', 'Unknown')}
- Software Used: {metadata.get('software', 'None detected')}
- Manipulation Risk Score: {risk_score}%

DETECTED INDICATORS:
{chr(10).join([f"- [{i['severity'].upper()}] {i['description']}" for i in indicators]) or '- None detected'}

Based on this forensic evidence, determine if the image is AI-generated or manipulated.
"""
        
        system_prompt, patterns_used = build_prompt_with_patterns('image')
        
        # Step 3: Now ask AI to analyze with forensic context
        completion = groq.chat.completions.create(
            model=Config.TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze image '{filename}':\n{forensic_evidence}"}
            ],
            temperature=0.7, max_tokens=1024
        )
        
        ai_response = completion.choices[0].message.content
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        
        if start != -1 and end > start:
            result = json.loads(ai_response[start:end])
            
            # ===== LEARNING BOOST: Adjust confidence based on learned patterns =====
            if patterns_used:
                original_confidence = result.get('confidence', 50)
                original_verdict = result.get('verdict', '')
                
                # Check if any learned patterns match this verdict
                matching_patterns = [p for p in patterns_used if p['verdict'] == original_verdict]
                
                if matching_patterns:
                    # Boost confidence when learned patterns support the verdict
                    boost = min(15, len(matching_patterns) * 5)  # +5 per pattern, max +15
                    new_confidence = min(95, original_confidence + boost)
                    result['confidence'] = new_confidence
                    result['learningBoost'] = f"+{boost}% from {len(matching_patterns)} learned patterns"
                
                # If no metadata (AI image indicator) and we have patterns saying "Fake"
                if not metadata.get('has_metadata'):
                    fake_patterns = [p for p in patterns_used if 'Fake' in p['verdict']]
                    if fake_patterns:
                        # Change verdict to Fake/Generated if AI said Inconclusive
                        if original_verdict == 'Inconclusive':
                            result['verdict'] = 'Fake/Generated'
                            result['confidence'] = max(70, result.get('confidence', 50))
                            result['learningAdjustment'] = 'Verdict changed from Inconclusive based on learned patterns'
            
            # Add forensics data
            if forensics and not forensics.get("error"):
                result["forensics"] = forensics
                result["technicalDetails"] = result.get("technicalDetails", [])
                
                if ela.get("performed"):
                    result["technicalDetails"].append({
                        "label": "ELA Analysis",
                        "value": f"Max error: {ela.get('max_error', 0)}%, Suspicious: {ela.get('suspicious_regions', 0)}%",
                        "status": "fail" if ela.get('max_error', 0) > 30 else "pass",
                        "explanation": "Error Level Analysis detects editing artifacts"
                    })
                
                if metadata.get("has_metadata"):
                    result["technicalDetails"].append({
                        "label": "EXIF Metadata",
                        "value": f"Camera: {metadata.get('camera', {}).get('Model', 'Unknown')}",
                        "status": "pass",
                        "explanation": "Original camera metadata preserved"
                    })
                else:
                    result["technicalDetails"].append({
                        "label": "EXIF Metadata", 
                        "value": "Missing - likely screenshot or AI-generated",
                        "status": "warn",
                        "explanation": "Real photos usually have camera metadata"
                    })
            
            # Add reverse search
            if reverse:
                result["reverseSearch"] = reverse.get("analysis", {})
                result["reverseSearch"]["matches"] = reverse.get("matches_found", 0)
                result["reverseSearch"]["manual_urls"] = reverse.get("manual_search_urls", {})
            
            result["riskScore"] = risk_score
            result["processingTime"] = f"{time.time() - start_time:.2f}s"
            result["learnedPatternsUsed"] = len(patterns_used)
            result["patternsApplied"] = patterns_used
            return jsonify(result)
        
        return jsonify({"error": "Invalid AI response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== VIDEO VERIFICATION ==========

@app.route('/api/verify/video', methods=['POST'])
def verify_video():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
        
        file = request.files['file']
        groq = get_client()
        
        completion = groq.chat.completions.create(
            model=Config.TEXT_MODEL,
            messages=[
                {"role": "system", "content": build_prompt_with_patterns('video')},
                {"role": "user", "content": f"Analyze: {file.filename}"}
            ],
            temperature=1, max_tokens=1024
        )
        
        response = completion.choices[0].message.content
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start != -1 and end > start:
            return jsonify(json.loads(response[start:end]))
        return jsonify({"error": "Invalid response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== AUDIO VERIFICATION ==========

@app.route('/api/verify/audio', methods=['POST'])
def verify_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
        
        file = request.files['file']
        groq = get_client()
        
        # Save temp file for Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as audio:
                transcription = groq.audio.transcriptions.create(
                    file=(file.filename, audio.read()),
                    model=Config.AUDIO_MODEL,
                    temperature=0
                )
            
            transcript = transcription.text
            
            completion = groq.chat.completions.create(
                model=Config.TEXT_MODEL,
                messages=[
                    {"role": "system", "content": build_prompt_with_patterns('audio')},
                    {"role": "user", "content": f"Analyze transcription:\n\n{transcript}"}
                ],
                temperature=1, max_tokens=1024
            )
            
            response = completion.choices[0].message.content
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                result = json.loads(response[start:end])
                result['transcription'] = transcript
                return jsonify(result)
            return jsonify({"error": "Invalid response"}), 500
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("VERITAS Backend API")
    print("=" * 50)
    print(f"Patterns: {get_stats()['total_patterns']}")
    print(f"Server: http://{Config.HOST}:{Config.PORT}")
    print("=" * 50)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
