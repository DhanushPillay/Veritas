"""
Veritas Chatbot - Flask Backend
A simple ChatGPT-like chatbot powered by Groq's LLaMA 4
"""

import os
import json
import uuid
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from groq import Groq

from config import Config

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

# Groq client (lazy initialization)
client = None

def get_client():
    """Get or create Groq client"""
    global client
    if client is None:
        client = Groq(api_key=Config.GROQ_API_KEY)
    return client


# In-memory conversation storage
# Structure: {conversation_id: {id, title, messages: [{role, content}], created_at}}
conversations = {}


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
        "conversations": len(conversations)
    })


# ========== CHAT API ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Send a message and get AI response.
    
    Request body:
    {
        "message": "Hello!",
        "conversation_id": "optional-uuid",
        "stream": false  // optional, for streaming responses
    }
    
    Response:
    {
        "response": "Hi there!",
        "conversation_id": "uuid",
        "message_id": "uuid"
    }
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        stream = data.get('stream', False)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get or create conversation
        if conversation_id and conversation_id in conversations:
            conversation = conversations[conversation_id]
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            conversation = {
                "id": conversation_id,
                "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "messages": [],
                "created_at": None  # Could add timestamp
            }
            conversations[conversation_id] = conversation
        
        # Add user message to history
        conversation["messages"].append({
            "role": "user",
            "content": user_message
        })
        
        # Build messages for Groq API
        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT}
        ] + conversation["messages"]
        
        groq = get_client()
        
        if stream:
            # Streaming response
            def generate():
                full_response = ""
                stream_response = groq.chat.completions.create(
                    model=Config.MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=True
                )
                
                for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                
                # Save assistant response to conversation
                conversation["messages"].append({
                    "role": "assistant",
                    "content": full_response
                })
                
                yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming response
            completion = groq.chat.completions.create(
                model=Config.MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            assistant_response = completion.choices[0].message.content
            
            # Save assistant response to conversation
            conversation["messages"].append({
                "role": "assistant",
                "content": assistant_response
            })
            
            return jsonify({
                "response": assistant_response,
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4())
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== CONVERSATION MANAGEMENT ==========

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations"""
    # Return conversations sorted by most recent (simplified - no timestamps yet)
    conv_list = [
        {
            "id": conv["id"],
            "title": conv["title"],
            "message_count": len(conv["messages"])
        }
        for conv in conversations.values()
    ]
    return jsonify({"conversations": conv_list})


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with all messages"""
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify(conversations[conversation_id])


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404
    
    del conversations[conversation_id]
    return jsonify({"success": True})


@app.route('/api/conversations', methods=['DELETE'])
def clear_all_conversations():
    """Delete all conversations"""
    conversations.clear()
    return jsonify({"success": True})


# ========== RUN ==========

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    VERITAS CHATBOT                           ║
║                                                              ║
║  Model: {Config.MODEL[:40]}...║
║  Server: http://{Config.HOST}:{Config.PORT}                          ║
║                                                              ║
║  Ready to chat!                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
