"""
Veritas Chatbot - Flask Backend
A ChatGPT-like chatbot powered by Groq's LLaMA 4 with web search capabilities
"""

import os
import json
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from config import Config
from web_search import search_web
from services.chat_service import chat_service

# Validate configuration
Config.validate()

# Get project root (parent of backend folder)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Setup Flask to serve static files from project root
app = Flask(__name__, 
            static_folder=PROJECT_ROOT,
            static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL), 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== FRONTEND ROUTES ==========

@app.route('/')
def serve_index():
    """Serve main index.html"""
    return app.send_static_file('index.html')


# ========== HEALTH CHECK ==========

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "model": Config.MODEL,
        "database": "supabase" if chat_service.use_persistent_storage() else "memory",
        "web_search": Config.WEB_SEARCH_ENABLED
    })


# ========== CHAT API ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Send a message and get AI response.
    Supports streaming for real-time responses.
    """
    try:
        data = request.json or {}
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        stream = data.get('stream', False)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        if stream:
            return Response(
                stream_with_context(chat_service.chat_stream(user_message, conversation_id)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            response_data = chat_service.chat_sync(user_message, conversation_id)
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ========== SEARCH API ==========

@app.route('/api/search', methods=['POST'])
def search():
    """Direct web search endpoint"""
    try:
        data = request.json or {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        results = search_web(query)
        
        return jsonify({
            "query": query,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Search API error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ========== CONVERSATION MANAGEMENT ==========

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations"""
    try:
        conversations = chat_service.get_all_conversations()
        return jsonify({"conversations": conversations})
    except Exception as e:
        logger.error(f"Get conversations error: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch conversations"}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_single_conversation(conversation_id):
    """Get a specific conversation with all messages"""
    try:
        conversation = chat_service.get_conversation(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify(conversation)
    except Exception as e:
        logger.error(f"Get conversation error: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch conversation"}), 500


@app.route('/api/conversations/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """Update a conversation (edit messages)"""
    try:
        data = request.json or {}
        conversation = chat_service.get_conversation(conversation_id)
        
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        if 'title' in data:
            conversation['title'] = data['title']
        
        if 'messages' in data:
            conversation['messages'] = data['messages']
        
        chat_service.save_conversation(conversation)
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Update conversation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation_endpoint(conversation_id):
    """Delete a conversation"""
    try:
        success = chat_service.delete_conversation(conversation_id)
        if not success:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Delete conversation error: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete conversation"}), 500


@app.route('/api/conversations', methods=['DELETE'])
def clear_all_conversations_endpoint():
    """Delete all conversations"""
    try:
        success = chat_service.clear_all_conversations()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Clear conversations error: {e}", exc_info=True)
        return jsonify({"error": "Failed to clear conversations"}), 500


# ========== RUN ==========

if __name__ == '__main__':
    db_status = "Supabase (persistent)" if chat_service.use_persistent_storage() else "Memory (session only)"
    search_status = "Enabled" if Config.WEB_SEARCH_ENABLED else "Disabled"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    VERITAS CHATBOT                           ║
║                                                              ║
║  Model: {Config.MODEL[:40]}...║
║  Database: {db_status:<43}║
║  Web Search: {search_status:<41}║
║  Server: http://{Config.HOST}:{Config.PORT}                          ║
║                                                              ║
║  Ready to chat!                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
