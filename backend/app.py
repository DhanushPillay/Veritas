"""
Veritas Chatbot - Flask Backend
A ChatGPT-like chatbot powered by Groq's LLaMA 4 with web search capabilities
"""

import os
import re
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from groq import Groq

from config import Config
from web_search import search_web, format_search_results

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
memory_conversations = {}


def use_persistent_storage():
    """Check if we should use persistent storage"""
    return USE_DATABASE and is_supabase_available()


def extract_search_query(response: str) -> str | None:
    """Extract search query from AI response if it requests a search"""
    # Look for [SEARCH: query] pattern
    match = re.search(r'\[SEARCH:\s*(.+?)\]', response, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def get_ai_response(messages: list, groq_client, use_search_context: bool = False) -> str:
    """Get a non-streaming response from the AI"""
    system_prompt = Config.SEARCH_CONTEXT_PROMPT if use_search_context else Config.SYSTEM_PROMPT
    
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    
    completion = groq_client.chat.completions.create(
        model=Config.MODEL,
        messages=full_messages,
        temperature=0.7,
        max_tokens=2048
    )
    
    return completion.choices[0].message.content


def process_with_search(user_message: str, conversation_messages: list, groq_client) -> tuple[str, bool]:
    """
    Process a message, potentially with web search.
    Returns (response, was_search_used)
    """
    # First, get initial AI response
    messages = conversation_messages + [{"role": "user", "content": user_message}]
    initial_response = get_ai_response(messages, groq_client)
    
    # Check if AI requested a search
    search_query = extract_search_query(initial_response)
    
    if search_query and Config.WEB_SEARCH_ENABLED:
        # Perform web search
        search_results = search_web(search_query)
        
        if search_results:
            # Format search results
            formatted_results = format_search_results(search_results)
            
            # Create new messages with search context
            search_context = f"""The user asked: "{user_message}"

I searched the web for: "{search_query}"

{formatted_results}

Based on these search results, please provide a helpful and accurate response to the user's question. 
Cite sources when appropriate."""
            
            # Get new response with search context
            messages_with_search = conversation_messages + [
                {"role": "user", "content": search_context}
            ]
            
            final_response = get_ai_response(messages_with_search, groq_client, use_search_context=True)
            return final_response, True
    
    return initial_response, False


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
        "web_search": Config.WEB_SEARCH_ENABLED,
        "conversations": len(memory_conversations)
    })


# ========== CHAT API ==========

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Send a message and get AI response.
    Supports streaming for real-time responses.
    Now with automatic web search for unknown topics.
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
        
        groq = get_client()
        
        if stream:
            # Streaming response with search support
            def generate():
                full_response = ""
                search_used = False
                
                try:
                    # Build messages for initial response
                    messages = [
                        {"role": "system", "content": Config.SYSTEM_PROMPT}
                    ] + conversation["messages"]
                    
                    # First pass - check if search is needed
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
                    
                    # Check if AI requested a search
                    search_query = extract_search_query(full_response)
                    
                    if search_query and Config.WEB_SEARCH_ENABLED:
                        # Notify user we're searching
                        yield f"data: {json.dumps({'content': '\\n\\n🔍 *Searching the web...*\\n\\n'})}\n\n"
                        
                        # Perform search
                        search_results = search_web(search_query)
                        
                        if search_results:
                            # Clear the old response indicator
                            full_response = ""
                            
                            # Format and send search context
                            formatted_results = format_search_results(search_results)
                            
                            search_context = f"""The user asked: "{user_message}"

I searched the web for: "{search_query}"

{formatted_results}

Based on these search results, please provide a helpful response. Cite sources."""
                            
                            # Get new response with search context
                            search_messages = [
                                {"role": "system", "content": Config.SEARCH_CONTEXT_PROMPT},
                                {"role": "user", "content": search_context}
                            ]
                            
                            search_stream = groq.chat.completions.create(
                                model=Config.MODEL,
                                messages=search_messages,
                                temperature=0.7,
                                max_tokens=2048,
                                stream=True
                            )
                            
                            for chunk in search_stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                            
                            search_used = True
                    
                    # Save assistant response
                    conversation["messages"].append({
                        "role": "assistant",
                        "content": full_response
                    })
                    conversation["updated_at"] = datetime.utcnow().isoformat()
                    
                    if use_persistent_storage():
                        save_conversation(conversation_id, conversation["title"], conversation["messages"])
                    else:
                        memory_conversations[conversation_id] = conversation
                    
                    yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id, 'search_used': search_used})}\n\n"
                    
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
            # Non-streaming response with search
            response, search_used = process_with_search(
                user_message, 
                conversation["messages"][:-1],  # Exclude the just-added user message
                groq
            )
            
            conversation["messages"].append({
                "role": "assistant",
                "content": response
            })
            conversation["updated_at"] = datetime.utcnow().isoformat()
            
            if use_persistent_storage():
                save_conversation(conversation_id, conversation["title"], conversation["messages"])
            else:
                memory_conversations[conversation_id] = response
            
            return jsonify({
                "response": response,
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "search_used": search_used
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== SEARCH API ==========

@app.route('/api/search', methods=['POST'])
def search():
    """Direct web search endpoint"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        results = search_web(query)
        
        return jsonify({
            "query": query,
            "results": results
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
            if isinstance(conv, dict)
        ]
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
        
        if 'title' in data:
            conversation['title'] = data['title']
        
        if 'messages' in data:
            conversation['messages'] = data['messages']
        
        conversation['updated_at'] = datetime.utcnow().isoformat()
        
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
