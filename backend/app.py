"""
Veritas Chatbot - Flask Backend
A ChatGPT-like chatbot powered by Groq's LLaMA 4
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from groq import Groq

from config import Config

# Try to import database module (optional Supabase)
try:
    from database import (
        is_supabase_available, save_conversation, get_conversation as db_get_conversation,
        get_all_conversations, delete_conversation as db_delete_conversation, clear_all_conversations
    )
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False

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


# In-memory conversation storage (fallback if no database)
# Structure: {conversation_id: {id, title, messages: [{role, content}], updated_at}}
memory_conversations = {}


def use_persistent_storage():
    """Check if we should use persistent storage"""
    return USE_DATABASE and is_supabase_available()


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
        "database": "supabase" if use_persistent_storage() else "memory",
        "conversations": len(memory_conversations)
    })


# ========== CHAT API ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Send a message and get AI response.
    Supports streaming for real-time responses.
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        stream = data.get('stream', False)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get or create conversation
        conversation = None
        if conversation_id:
            if use_persistent_storage():
                conversation = db_get_conversation(conversation_id)
            else:
                conversation = memory_conversations.get(conversation_id)
        
        if not conversation:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            conversation = {
                "id": conversation_id,
                "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "messages": [],
                "updated_at": datetime.utcnow().isoformat()
            }
        
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
                try:
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
                    conversation["updated_at"] = datetime.utcnow().isoformat()
                    
                    # Save to storage
                    if use_persistent_storage():
                        save_conversation(conversation_id, conversation["title"], conversation["messages"])
                    else:
                        memory_conversations[conversation_id] = conversation
                    
                    yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
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
            conversation["updated_at"] = datetime.utcnow().isoformat()
            
            # Save to storage
            if use_persistent_storage():
                save_conversation(conversation_id, conversation["title"], conversation["messages"])
            else:
                memory_conversations[conversation_id] = conversation
            
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
    if use_persistent_storage():
        conversations = get_all_conversations()
        conv_list = [
            {
                "id": conv["id"],
                "title": conv["title"],
                "updated_at": conv.get("updated_at")
            }
            for conv in conversations
        ]
    else:
        conv_list = [
            {
                "id": conv["id"],
                "title": conv["title"],
                "message_count": len(conv["messages"]),
                "updated_at": conv.get("updated_at")
            }
            for conv in memory_conversations.values()
        ]
        # Sort by updated_at descending
        conv_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return jsonify({"conversations": conv_list})


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_single_conversation(conversation_id):
    """Get a specific conversation with all messages"""
    if use_persistent_storage():
        conversation = db_get_conversation(conversation_id)
    else:
        conversation = memory_conversations.get(conversation_id)
    
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify(conversation)


@app.route('/api/conversations/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """Update a conversation (edit messages)"""
    try:
        data = request.json
        
        if use_persistent_storage():
            conversation = db_get_conversation(conversation_id)
        else:
            conversation = memory_conversations.get(conversation_id)
        
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Update title if provided
        if 'title' in data:
            conversation['title'] = data['title']
        
        # Update messages if provided
        if 'messages' in data:
            conversation['messages'] = data['messages']
        
        conversation['updated_at'] = datetime.utcnow().isoformat()
        
        # Save
        if use_persistent_storage():
            save_conversation(conversation_id, conversation['title'], conversation['messages'])
        else:
            memory_conversations[conversation_id] = conversation
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation_endpoint(conversation_id):
    """Delete a conversation"""
    if use_persistent_storage():
        success = db_delete_conversation(conversation_id)
    else:
        success = conversation_id in memory_conversations
        if success:
            del memory_conversations[conversation_id]
    
    if not success:
        return jsonify({"error": "Conversation not found"}), 404
    
    return jsonify({"success": True})


@app.route('/api/conversations', methods=['DELETE'])
def clear_all_conversations_endpoint():
    """Delete all conversations"""
    if use_persistent_storage():
        clear_all_conversations()
    else:
        memory_conversations.clear()
    
    return jsonify({"success": True})


# ========== RUN ==========

if __name__ == '__main__':
    db_status = "Supabase (persistent)" if use_persistent_storage() else "Memory (session only)"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    VERITAS CHATBOT                           ║
║                                                              ║
║  Model: {Config.MODEL[:40]}...║
║  Database: {db_status:<43}║
║  Server: http://{Config.HOST}:{Config.PORT}                          ║
║                                                              ║
║  Ready to chat!                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
