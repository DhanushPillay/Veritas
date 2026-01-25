# Veritas - AI Chatbot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-red?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**A ChatGPT-style AI chatbot powered by Groq's LLaMA 4**

</div>

---

## ✨ Features

### Chat
- 💬 **Streaming Responses** - Real-time typing effect
- 🧠 **Conversation Memory** - Maintains context within sessions
- ✏️ **Message Editing** - Edit and regenerate responses
- 🔄 **Regenerate** - Retry any response
- ⏹️ **Stop Generation** - Cancel mid-response (Esc key)

### UI/UX
- 🌙 **Dark/Light Theme** - Toggle with persistence
- 🔍 **Search Conversations** - Filter your chat history
- 📋 **Copy Code** - One-click copy with syntax highlighting  
- 📤 **Export Chat** - Download as Markdown
- ⌨️ **Keyboard Shortcuts** - Ctrl+N, Esc, Ctrl+Shift+C

### Storage
- 💾 **Persistent Storage** - Supabase integration (optional)
- 🗄️ **Memory Fallback** - Works without database

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Groq API Key ([Get one free](https://console.groq.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/DhanushPillay/Veritas.git
cd Veritas

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
# Edit backend/.env and add your GROQ_API_KEY
```

### Run

```bash
cd backend
python app.py
```

Open http://localhost:5000 in your browser.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line |
| `Ctrl + N` | New chat |
| `Esc` | Stop generation |
| `Ctrl + Shift + C` | Copy last response |

---

## 📁 Project Structure

```
Veritas/
├── backend/
│   ├── app.py           # Flask API server
│   ├── config.py        # Configuration
│   ├── database.py      # Supabase client
│   ├── requirements.txt # Dependencies
│   └── .env             # API keys (create this)
├── frontend/
│   ├── css/styles.css   # Dark/Light theme styling
│   └── js/app.js        # Chat functionality
└── index.html           # Main page
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message (supports streaming) |
| `/api/conversations` | GET | List all conversations |
| `/api/conversations/<id>` | GET | Get conversation history |
| `/api/conversations/<id>` | PUT | Update conversation |
| `/api/conversations/<id>` | DELETE | Delete conversation |
| `/api/health` | GET | Health check |

---

## 🔧 Configuration

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key

# Optional: Supabase for persistent storage
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Supabase Setup (Optional)

Create a `conversations` table:

```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  title TEXT,
  messages JSONB,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🛠️ Tech Stack

- **Backend**: Flask + Groq API (LLaMA 4)
- **Frontend**: Vanilla HTML/CSS/JS
- **Styling**: CSS Variables (Dark/Light themes)
- **Markdown**: Marked.js
- **Syntax Highlighting**: Highlight.js
- **Database**: Supabase (optional)

---

## 📜 License

MIT License

---

**Developed by Dhanush Pillay**
