# Veritas - AI Chatbot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-red?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**A ChatGPT-style AI chatbot powered by Groq's LLaMA 4**

</div>

---

## ✨ Features

### Chat Intelligence
- 💬 **Smart Streaming** - Real-time typing effect like the real thing
- 🧠 **Context Awareness** - Remembers your conversation history
- 🌐 **Web Search** - Automatically searches the web for current info
- ✏️ **Message Editing** - Fix typos or change prompts mid-chat
- 🔄 **Regenerate** - Not happy? Get a better response instantly
- ⏹️ **Stop Generation** - Interrupt long responses safely

### Premium UI/UX
- 🌙 **Adaptive Theme** - Beautiful Dark & Light modes
- 🎨 **Syntax Highlighting** - Clean code blocks with language detection
- 📋 **One-Click Copy** - Grab code snippets instantly
- 🔍 **Search History** - Find past conversations in seconds
- 📤 **Export Chat** - Save conversations as Markdown for sharing

### Power Features
- ⌨️ **Keyboard Shortcuts** - Ctrl+N (New Chat), Esc (Stop), Ctrl+Shift+C (Copy)
- 💾 **Auto-Save** - Never lose a chat (uses Supabase or local memory)
- 📱 **Mobile Ready** - Fully responsive design for any device

---

## ⌨️ Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line |
| `Ctrl + N` | Start new chat |
| `Esc` | Stop generating |
| `Ctrl + Shift + C` | Copy last response |

---

## � API Overview

### Chat & Search
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message (auto-detects if search needed) |
| `/api/search` | POST | Direct web search (DuckDuckGo provider) |

### Conversation Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations` | GET | List history |
| `/api/conversations/<id>` | GET/PUT/DEL | Manage specific chat |

---

## �️ Tech Stack

- **AI Core**: Groq API (LLaMA 4)
- **Backend**: Flask (Python)
- **Frontend**: Vanilla JS + CSS3 (No heavy frameworks)
- **Search**: DuckDuckGo API
- **Storage**: Supabase (Optional)
- **Rendering**: Marked.js + Highlight.js

---

## 📜 License

MIT License

---

**Developed by Dhanush Pillay**
