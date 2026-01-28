"""
Chat Service for Veritas
Handles the core logic for chatting with the AI, including:
- Conversation management
- Web search integration
- Streaming and synchronous responses
"""

import json
import uuid
import re
import logging
from datetime import datetime
from groq import Groq

from config import Config
from web_search import search_web, format_search_results

# Try to import database module
try:
    from database import (
        is_supabase_available, save_conversation, get_conversation as db_get_conversation,
        get_all_conversations, delete_conversation as db_delete_conversation, clear_all_conversations
    )
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.client = None
        # In-memory storage fallback
        self.memory_conversations = {}

    def get_client(self):
        """Get or create Groq client"""
        if self.client is None:
            self.client = Groq(api_key=Config.GROQ_API_KEY)
        return self.client

    def use_persistent_storage(self):
        """Check if we should use persistent storage"""
        return USE_DATABASE and is_supabase_available()

    def get_conversation(self, conversation_id: str):
        """Get a conversation by ID from DB or memory"""
        if not conversation_id:
            return None
            
        if self.use_persistent_storage():
            return db_get_conversation(conversation_id)
        else:
            return self.memory_conversations.get(conversation_id)

    def save_conversation(self, conversation):
        """Save conversation to DB or memory"""
        conversation["updated_at"] = datetime.utcnow().isoformat()
        
        if self.use_persistent_storage():
            save_conversation(conversation["id"], conversation["title"], conversation["messages"])
        else:
            self.memory_conversations[conversation["id"]] = conversation.copy()

    def create_conversation(self, initial_message: str):
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        conversation = {
            "id": conversation_id,
            "title": initial_message[:50] + "..." if len(initial_message) > 50 else initial_message,
            "messages": [],
            "updated_at": datetime.utcnow().isoformat()
        }
        return conversation

    def _extract_search_query(self, response: str) -> str | None:
        """Extract search query from AI response if it requests a search"""
        match = re.search(r'\[SEARCH:\s*(.+?)\]', response, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _get_ai_response(self, messages: list, use_search_context: bool = False) -> str:
        """Get a non-streaming response from the AI"""
        groq = self.get_client()
        system_prompt = Config.SEARCH_CONTEXT_PROMPT if use_search_context else Config.SYSTEM_PROMPT
        
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        completion = groq.chat.completions.create(
            model=Config.MODEL,
            messages=full_messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        return completion.choices[0].message.content

    def chat_sync(self, user_message: str, conversation_id: str = None) -> dict:
        """Handle a synchronous chat request"""
        # Get or create conversation
        conversation = self.get_conversation(conversation_id) if conversation_id else None
        if not conversation:
            conversation = self.create_conversation(user_message)
            conversation_id = conversation["id"]

        # Add user message
        conversation["messages"].append({
            "role": "user",
            "content": user_message
        })
        
        response, search_used = self._process_with_search(
            user_message,
            conversation["messages"][:-1]  # Exclude current message for context to avoid duplication if handled internally? 
            # Actually, _process_with_search takes conversation_messages and ADDS user_message.
            # My logic in app.py passed `conversation["messages"][:-1]` because it had already appended the message.
        )
        
        # Save assistant response
        conversation["messages"].append({
            "role": "assistant",
            "content": response
        })
        self.save_conversation(conversation)
        
        return {
            "response": response,
            "conversation_id": conversation_id,
            "message_id": str(uuid.uuid4()),
            "search_used": search_used
        }

    def _process_with_search(self, user_message: str, context_messages: list) -> tuple[str, bool]:
        """Process message with potential search"""
        # Initial response
        messages = context_messages + [{"role": "user", "content": user_message}]
        initial_response = self._get_ai_response(messages)
        
        search_query = self._extract_search_query(initial_response)
        
        if search_query and Config.WEB_SEARCH_ENABLED:
            search_results = search_web(search_query)
            
            if search_results:
                formatted_results = format_search_results(search_results)
                
                search_context = f"""The user asked: "{user_message}"

I searched the web for: "{search_query}"

{formatted_results}

Based on these search results, please provide a helpful and accurate response to the user's question. 
Cite sources when appropriate."""
                
                messages_with_search = context_messages + [
                    {"role": "user", "content": search_context}
                ]
                
                final_response = self._get_ai_response(messages_with_search, use_search_context=True)
                return final_response, True
        
        return initial_response, False

    def chat_stream(self, user_message: str, conversation_id: str = None):
        """Generator for streaming chat response"""
        # Get or create conversation
        conversation = self.get_conversation(conversation_id) if conversation_id else None
        if not conversation:
            conversation = self.create_conversation(user_message)
            conversation_id = conversation["id"]
            
        # Add user message
        conversation["messages"].append({
            "role": "user",
            "content": user_message
        })

        groq = self.get_client()
        full_response = ""
        search_used = False

        try:
            # Build messages
            messages = [{"role": "system", "content": Config.SYSTEM_PROMPT}] + conversation["messages"]

            # 1. Initial Stream
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

            # 2. Check for Search
            search_query = self._extract_search_query(full_response)
            
            if search_query and Config.WEB_SEARCH_ENABLED:
                yield f"data: {json.dumps({'content': '\\n\\n🔍 *Searching the web...*\\n\\n'})}\n\n"
                
                search_results = search_web(search_query)
                
                if search_results:
                    # Clear accumulator
                    full_response = ""
                    
                    formatted_results = format_search_results(search_results)
                    search_context = f"""The user asked: "{user_message}"

I searched the web for: "{search_query}"

{formatted_results}

Based on these search results, please provide a helpful response. Cite sources."""

                    # New stream with search context
                    # Note: We must NOT include the original failed/search-requesting assistant response in context
                    # So we use conversation messages up to the user message, but replace the user message content?
                    # Or just append the search context as a NEW user message?
                    # app.py logic was: 
                    # Use `conversation["messages"]` (which includes user msg) -> 1st pass
                    # If search -> 
                    # `search_messages` = [System(SearchPrompt), User(SearchContext)]
                    # This seems to drop previous context?
                    # Let's check app.py trace.
                    # app.py:
                    # search_messages = [ {"role": "system", ...}, {"role": "user", "content": search_context} ]
                    # Yes, it drops previous conversation context in the search pass! This might be a bug or feature.
                    # Ideally it should keep history.
                    # But for now I will replicate app.py behavior to be safe.
                    
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

            # 3. Save Response
            conversation["messages"].append({
                "role": "assistant",
                "content": full_response
            })
            self.save_conversation(conversation)
            
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id, 'search_used': search_used})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def get_all_conversations(self, limit: int = 50) -> list:
        """Get all conversations"""
        if self.use_persistent_storage():
            conversations = get_all_conversations(limit)
            return [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "updated_at": conv.get("updated_at")
                }
                for conv in conversations
            ]
        else:
            # Memory implementation
            conv_list = [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "message_count": len(conv["messages"]),
                    "updated_at": conv.get("updated_at")
                }
                for conv in self.memory_conversations.values()
                if isinstance(conv, dict)
            ]
            conv_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return conv_list[:limit]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if self.use_persistent_storage():
            return db_delete_conversation(conversation_id)
        else:
            if conversation_id in self.memory_conversations:
                del self.memory_conversations[conversation_id]
                return True
            return False

    def clear_all_conversations(self) -> bool:
        """Clear all conversations"""
        if self.use_persistent_storage():
            return clear_all_conversations()
        else:
            self.memory_conversations.clear()
            return True

# Singleton instance
chat_service = ChatService()
