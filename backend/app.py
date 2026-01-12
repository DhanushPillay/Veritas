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
from external.factcheck import FactCheckService, search_news_for_claim, search_web_context, scrape_url_content
from external.supabase_client import (
    upload_media, delete_media, save_analysis, get_history, get_analysis, delete_analysis
)
from forensics.image_forensics import analyze_image_bytes
from forensics.reverse_search import search_image
from forensics.c2pa_detector import detect_c2pa
from forensics.synthid_detector import detect_synthid
from forensics.visual_detector import detect_visual_patterns
from learning.text_detector import detect_ai_text, is_model_available

# Initialize
Config.validate()

# Get the project root (parent of backend folder)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Setup Flask to serve static files from project root
app = Flask(__name__, 
            static_folder=PROJECT_ROOT,
            static_url_path='')
CORS(app)

# Configure max upload size to 3GB
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024 * 1024

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
    "verdict": "Authentic" | "AI-Generated" | "Inconclusive" | "Suspicious",
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


# ========== FRONTEND ROUTES ==========

@app.route('/')
def serve_index():
    """Serve main index.html"""
    return app.send_static_file('index.html')

@app.route('/frontend/pages/<path:filename>')
def serve_pages(filename):
    """Serve pages from frontend/pages/"""
    return app.send_static_file(f'frontend/pages/{filename}')


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


# ========== HISTORY API ==========

@app.route('/api/history', methods=['GET'])
def get_history_endpoint():
    """Get recent analysis history from Supabase."""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = get_history(limit=limit)
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/history/<record_id>', methods=['GET'])
def get_history_item(record_id):
    """Get a single history item."""
    try:
        record = get_analysis(record_id)
        if record:
            return jsonify(record)
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/history/<record_id>', methods=['DELETE'])
def delete_history_item(record_id):
    """Delete a history item and its associated media."""
    try:
        success = delete_analysis(record_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== TEXT INTENT DETECTION ==========

def detect_text_intent(text: str) -> dict:
    """
    Auto-detect what type of analysis the text needs.
    Returns: {
        'primary': 'fact_check' | 'ai_detection' | 'both',
        'reason': str,
        'indicators': list
    }
    """
    text_lower = text.lower().strip()
    word_count = len(text.split())
    
    indicators = []
    
    # --- Fact-check indicators ---
    fact_check_score = 0
    
    # Questions typically need fact-checking
    if text_lower.endswith('?') or text_lower.startswith(('is ', 'are ', 'was ', 'were ', 'did ', 'does ', 'do ', 'can ', 'could ', 'will ', 'would ', 'should ', 'has ', 'have ', 'what ', 'when ', 'where ', 'who ', 'why ', 'how ')):
        fact_check_score += 3
        indicators.append("Question detected")
    
    # Claims with specific entities (numbers, dates, names)
    import re
    if re.search(r'\d{4}', text):  # Years
        fact_check_score += 1
        indicators.append("Contains dates/years")
    if re.search(r'\d+%|\d+ percent', text_lower):  # Percentages
        fact_check_score += 2
        indicators.append("Contains statistics")
    if re.search(r'"[^"]+"', text):  # Quoted text
        fact_check_score += 2
        indicators.append("Contains quotes")
    
    # Claim keywords
    claim_keywords = ['claimed', 'stated', 'said', 'according to', 'reported', 'announced', 'confirmed', 'denied', 'true', 'false', 'fake', 'real', 'myth', 'fact']
    if any(kw in text_lower for kw in claim_keywords):
        fact_check_score += 2
        indicators.append("Contains claim language")
    
    # --- AI detection indicators ---
    ai_detection_score = 0
    
    # Long-form content (articles, essays)
    if word_count > 150:
        ai_detection_score += 3
        indicators.append("Long-form content")
    elif word_count > 50:
        ai_detection_score += 1
        indicators.append("Medium-length content")
    
    # Essay/article patterns
    if any(phrase in text_lower for phrase in ['in conclusion', 'furthermore', 'moreover', 'in summary', 'to summarize', 'in this article', 'this essay']):
        ai_detection_score += 2
        indicators.append("Essay/article structure")
    
    # Generic/placeholder language (AI often uses)
    generic_patterns = ['it is important to note', 'it is worth noting', 'one could argue', 'it can be said', 'in today\'s world', 'in the modern era']
    if any(p in text_lower for p in generic_patterns):
        ai_detection_score += 2
        indicators.append("Generic AI-like phrasing")
    
    # --- Determine primary intent ---
    if fact_check_score >= 3 and ai_detection_score < 2:
        return {
            'primary': 'fact_check',
            'reason': 'Text appears to be a claim or question needing verification',
            'indicators': indicators,
            'scores': {'fact_check': fact_check_score, 'ai_detection': ai_detection_score}
        }
    elif ai_detection_score >= 3 and fact_check_score < 2:
        return {
            'primary': 'ai_detection',
            'reason': 'Text appears to be content that should be checked for AI authorship',
            'indicators': indicators,
            'scores': {'fact_check': fact_check_score, 'ai_detection': ai_detection_score}
        }
    else:
        return {
            'primary': 'both',
            'reason': 'Text needs both fact-checking and AI detection analysis',
            'indicators': indicators,
            'scores': {'fact_check': fact_check_score, 'ai_detection': ai_detection_score}
        }


# ========== TEXT VERIFICATION ==========

@app.route('/api/verify/text', methods=['POST'])
def verify_text():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    try:
        start_time = time.time()
        data = request.json
        text = data.get('text', '')
        use_search = data.get('useSearch', True)  # Default to True (Always On Search)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Auto-detect what type of analysis is needed
        intent = detect_text_intent(text)
        
        # Check if text is a URL
        is_url = text.strip().startswith(('http://', 'https://'))
        scraped_content = ""
        
        if is_url:
            scraped_content = scrape_url_content(text.strip())
            if scraped_content:
                # Use scraped content for analysis, but keep URL as source
                analysis_text = scraped_content
                base_prompt = f"Fact-check the content of this article ({text}):\n\n{analysis_text[:2000]}..."
            else:
                analysis_text = text
                base_prompt = f"Fact-check this link (I could not scrape it, so relying on search): {text}"
        else:
            analysis_text = text
            base_prompt = f"Fact-check this text:\n\n{text}"
        
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
        
        factcheck_results = []
        news_results = []
        web_results = []
        
        if use_search:
            # 1. Run searches in parallel
            # Create search query from text (first 200 chars or key terms)
            search_query = analysis_text[:200]
            
            with ThreadPoolExecutor(max_workers=4) as ex:
                futures = {
                    ex.submit(factcheck.search_claims, search_query): "fc",
                    ex.submit(search_news_for_claim, search_query[:100]): "news",
                    ex.submit(search_web_context, search_query): "web"
                }
                
                for f in as_completed(futures):
                    name = futures[f]
                    try:
                        res = f.result()
                        if name == "fc": factcheck_results = res
                        elif name == "news": news_results = res
                        elif name == "web": web_results = res
                    except Exception as e:
                        print(f"Search error {name}: {e}")
            
            # 2. Build context for AI
            context = ""
            if factcheck_results:
                context += "\n[VERIFIED FACT CHECKS]\n" + "\n".join([f"- {f['title']}: {f['rating']}" for f in factcheck_results[:3]])
            if news_results:
                context += "\n[LATEST NEWS]\n" + "\n".join([f"- {n['title']} ({n['source']})" for n in news_results[:3]])
            if web_results:
                context += "\n[WEB CONTEXT]\n" + "\n".join([f"- {w['snippet']}" for w in web_results[:3]])
            
            if context:
                base_prompt += f"\n\nSEARCH CONTEXT:{context}\nUse this context to verify the claim."

        # 2.5. Run ML-based AI text detection (if model available)
        ml_detection = None
        if is_model_available():
            try:
                ml_detection = detect_ai_text(analysis_text)
            except Exception as e:
                print(f"ML text detection error: {e}")

        # 3. Run AI
        ai_response = run_ai(base_prompt)
        
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        
        if start != -1 and end > start:
            result = json.loads(ai_response[start:end])
            # Combine sources
            sources = result.get('sources', [])
            
            if factcheck_results:
                boost = factcheck.get_credibility_boost(factcheck_results)
                sources.extend([{'title': f"{fc['publisher']}: {fc['rating']}", 'uri': fc['url']} for fc in factcheck_results])
                result['factCheckSummary'] = boost['summary']
            
            if web_results:
                # Add web results to sources
                sources.extend([{'title': w['title'], 'uri': w['url']} for w in web_results])
            
            if sources:
                result['sources'] = sources

            if news_results:
                result['relatedNews'] = news_results
            
            # Add ML-based text detection results
            if ml_detection and not ml_detection.get('error'):
                result['aiTextDetection'] = ml_detection
                
                # Boost confidence if ML model strongly indicates AI-generated
                if ml_detection.get('is_ai') and ml_detection.get('confidence', 0) > 75:
                    result['technicalDetails'] = result.get('technicalDetails', [])
                    result['technicalDetails'].append({
                        'label': 'ML Text Detection',
                        'value': f"AI-Generated: {ml_detection['confidence']:.1f}% confidence",
                        'status': 'fail',
                        'explanation': 'Trained DistilBERT model detected AI writing patterns'
                    })
                    
                    # Adjust verdict if ML is confident but AI says otherwise
                    if result.get('verdict') == 'Authentic' and ml_detection['confidence'] > 85:
                        result['verdict'] = 'Suspicious'
                        result['mlOverride'] = 'ML model detected high probability of AI-generated content'
                
                elif not ml_detection.get('is_ai') and ml_detection.get('confidence', 0) > 75:
                    result['technicalDetails'] = result.get('technicalDetails', [])
                    result['technicalDetails'].append({
                        'label': 'ML Text Detection',
                        'value': f"Human-Written: {ml_detection['confidence']:.1f}% confidence",
                        'status': 'pass',
                        'explanation': 'Trained DistilBERT model indicates human writing patterns'
                    })
            
            result['processingTime'] = f"{time.time() - start_time:.2f}s"
            result['learnedPatternsUsed'] = len(patterns_used)
            result['patternsApplied'] = patterns_used
            
            # Add intent analysis info for clear UI display
            result['analysisType'] = {
                'primary': intent['primary'],
                'reason': intent['reason'],
                'indicators': intent['indicators']
            }
            
            # Structure results clearly by type
            result['analysisResults'] = {
                'factCheck': {
                    'enabled': intent['primary'] in ['fact_check', 'both'],
                    'verdict': result.get('verdict'),
                    'confidence': result.get('confidence'),
                    'summary': result.get('summary'),
                    'sources': result.get('sources', []),
                    'factCheckSummary': result.get('factCheckSummary')
                },
                'aiDetection': {
                    'enabled': intent['primary'] in ['ai_detection', 'both'],
                    'result': ml_detection if ml_detection and not ml_detection.get('error') else None,
                    'isAiGenerated': ml_detection.get('is_ai') if ml_detection else None,
                    'confidence': ml_detection.get('confidence') if ml_detection else None
                }
            }
            
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
        
        # Step 1: Run forensics and watermark detection in parallel
        with ThreadPoolExecutor(max_workers=5) as ex:
            forensics_future = ex.submit(analyze_image_bytes, content, filename)
            reverse_future = ex.submit(search_image, content)
            c2pa_future = ex.submit(detect_c2pa, content)
            synthid_future = ex.submit(detect_synthid, content)
            visual_future = ex.submit(detect_visual_patterns, content)
            
            forensics = forensics_future.result()
            reverse = reverse_future.result()
            c2pa_result = c2pa_future.result()
            synthid_result = synthid_future.result()
            visual_result = visual_future.result()
        
        # Build watermark detection summary
        watermarks = {
            "c2pa": {
                "detected": c2pa_result.get("detected", False),
                "source": c2pa_result.get("source"),
                "confidence": c2pa_result.get("confidence", 0)
            },
            "synthid": {
                "detected": synthid_result.get("detected", False),
                "confidence": synthid_result.get("confidence", 0)
            },
            "visual_ai": {
                "detected": visual_result.get("detected", False),
                "confidence": visual_result.get("confidence", 0),
                "indicators": visual_result.get("indicators", [])
            }
        }
        
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
            
            # Add watermark detection results
            result["watermarks"] = watermarks
            
            # ===== WATERMARK BOOST: Increase confidence if watermarks detected =====
            watermark_boost = 0
            watermark_sources = []
            
            if c2pa_result.get("detected"):
                watermark_boost += 20  # C2PA is strong evidence
                watermark_sources.append(f"C2PA ({c2pa_result.get('source', 'AI')})")
            
            if synthid_result.get("detected"):
                watermark_boost += 15
                watermark_sources.append("SynthID")
            
            if visual_result.get("detected"):
                # Add based on visual confidence
                visual_boost = min(15, visual_result.get("confidence", 0) // 5)
                watermark_boost += visual_boost
                watermark_sources.append("Visual AI Patterns")
            
            if watermark_boost > 0:
                # ABSOLUTE OVERRIDE: If any watermark is detected, it is 100% fake.
                result["confidence"] = 100
                result["verdict"] = "AI-Generated"
                result["watermarkBoost"] = "Definitive Proof: AI Watermark Detected"
                result["verdictAdjustment"] = f"Override: {', '.join(watermark_sources)} found."
            
            # Add watermark tech details
            if c2pa_result.get("detected"):
                result["technicalDetails"].append({
                    "label": "C2PA Watermark",
                    "value": f"Source: {c2pa_result.get('source', 'Unknown')}",
                    "status": "fail",
                    "explanation": f"AI generation signature detected (DALL-E/Adobe/etc)"
                })
            
            if synthid_result.get("detected"):
                result["technicalDetails"].append({
                    "label": "SynthID",
                    "value": f"Confidence: {synthid_result.get('confidence', 0)}%",
                    "status": "fail",
                    "explanation": "Google AI watermark detected"
                })
            
            if visual_result.get("detected"):
                indicators_text = ", ".join(visual_result.get("indicators", [])[:2]) or "Pattern anomalies"
                result["technicalDetails"].append({
                    "label": "Visual AI Patterns",
                    "value": f"Confidence: {visual_result.get('confidence', 0)}%",
                    "status": "fail",
                    "explanation": indicators_text
                })
            
            result["riskScore"] = risk_score
            result["processingTime"] = f"{time.time() - start_time:.2f}s"
            result["learnedPatternsUsed"] = len(patterns_used)
            result["patternsApplied"] = patterns_used
            
            # ========== SAVE TO SUPABASE ==========
            try:
                # Upload media to Supabase Storage
                media_url = None
                thumbnail_url = None
                
                try:
                    media_url = upload_media(file_bytes, file.filename, file.content_type)
                except Exception as upload_err:
                    print(f"Media upload failed (non-fatal): {upload_err}")
                
                # Save analysis record to database
                save_analysis({
                    "type": "image",
                    "preview": file.filename[:60] if file.filename else "Unknown",
                    "media_url": media_url,
                    "thumbnail_url": thumbnail_url,  # Generated client-side, not available here
                    "result": result,
                    "verdict": result.get("verdict"),
                    "confidence": result.get("confidence", 0)
                })
            except Exception as db_err:
                print(f"Supabase save failed (non-fatal): {db_err}")
            
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
