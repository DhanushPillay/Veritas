# Veritas - AI Chatbot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-red?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**A ChatGPT-style AI chatbot powered by Groq's LLaMA 4**

</div>

---

## Features

- 💬 **Real-time Chat** - Fast responses powered by Groq API
- 🧠 **Conversation Memory** - Maintains context within sessions
- 🌙 **Dark Theme** - Modern ChatGPT-inspired UI
- 📱 **Responsive Design** - Works on desktop and mobile
- ✨ **Markdown Support** - Code blocks, lists, and formatting

---

## Quick Start

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
cp backend/.env.example backend/.env
# Edit .env and add your GROQ_API_KEY
```

### Run

```bash
cd backend
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Project Structure

```
Veritas/
├── backend/
│   ├── app.py           # Flask API server
│   ├── config.py        # Configuration
│   ├── requirements.txt # Dependencies
│   └── .env             # API keys (create this)
├── frontend/
│   ├── css/styles.css   # Dark theme styling
│   └── js/app.js        # Chat functionality
└── index.html           # Main page
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get response |
| `/api/conversations` | GET | List all conversations |
| `/api/conversations/<id>` | GET | Get conversation history |
| `/api/conversations/<id>` | DELETE | Delete conversation |
| `/api/health` | GET | Health check |

---

## Tech Stack

- **Backend**: Flask + Groq API (LLaMA 4)
- **Frontend**: Vanilla HTML/CSS/JS
- **Styling**: Custom CSS with CSS Variables
- **Markdown**: Marked.js

---

## License

MIT License

---

**Developed by Dhanush Pillay**
