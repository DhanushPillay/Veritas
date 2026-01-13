# VERITAS - AI-Powered Media Verification System

<div align="center">

![Veritas Logo](https://img.shields.io/badge/VERITAS-Media_Verification-blue?style=for-the-badge&logo=shield)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-red?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Detect deepfakes, AI-generated content, and misinformation with advanced AI forensics.**

</div>

---

## 🎯 Features

### 🤖 AI Text Detection (NEW!)
- **Custom-trained ML model** using DistilBERT
- Detects AI-generated vs human-written text
- 60/40 ensemble combining ML model + Groq AI
- Separate dedicated tab for fast detection

### 🔍 Fact Checking
- Verifies claims using web search + AI analysis
- Finds sources and cross-references information
- Uses Groq's LLaMA 4 for reasoning

### 🖼️ Image Analysis
- Detects AI-generated images and deepfakes
- Error Level Analysis (ELA) forensics
- C2PA, SynthID watermark detection
- Reverse image search integration

### 🎥 Video Forensics
- Frame-by-frame deepfake detection
- Lip-sync analysis
- Face manipulation detection

### 🎤 Audio Analysis
- Voice cloning detection
- Speech-to-text transcription (Whisper)
- Audio splicing identification

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Vanilla JS)                  │
│  ┌──────────┐ ┌────────────┐ ┌───────┐ ┌───────┐ ┌───────┐ │
│  │AI Detect │ │ Fact Check │ │ Image │ │ Audio │ │ Video │ │
│  └────┬─────┘ └─────┬──────┘ └───┬───┘ └───┬───┘ └───┬───┘ │
└───────┼─────────────┼────────────┼─────────┼─────────┼─────┘
        │             │            │         │         │
        ▼             ▼            ▼         ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FLASK BACKEND (Python)                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API ENDPOINTS                           │   │
│  │  /api/detect/ai-text  →  ML Model Only (Fast)       │   │
│  │  /api/verify/text     →  Ensemble (ML + Groq)       │   │
│  │  /api/verify/image    →  Forensics + Groq           │   │
│  │  /api/verify/audio    →  Whisper + Analysis         │   │
│  │  /api/verify/video    →  Frame Analysis + Groq      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ Your Trained  │  │   Groq API    │  │   Forensics    │  │
│  │ DistilBERT    │  │   (LLaMA 4)   │  │   (ELA, C2PA)  │  │
│  │ (Local Model) │  │   (Remote)    │  │   (Local)      │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js (optional, for development)
- Groq API Key (free at [console.groq.com](https://console.groq.com))

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

### Run the Application

```bash
cd backend
python app.py
```

Open `http://localhost:5000` in your browser.

---

## 🧠 ML Models

### Custom-Trained Model (Text Detection)
| Model | Base | Dataset | Purpose |
|-------|------|---------|---------|
| `veritas_text_detector` | DistilBERT | ai-text-detection-pile | AI vs Human text |

### Groq API Models (Pre-trained)
| Model | Purpose | Trainable |
|-------|---------|-----------|
| LLaMA 4 Scout 17B | Text & Image reasoning | ❌ |
| Whisper Large v3 Turbo | Audio transcription | ❌ |

---

## 📁 Project Structure

```
Veritas/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration and API keys
│   ├── forensics/             # Image forensics tools
│   │   ├── c2pa_detector.py   # C2PA watermark detection
│   │   ├── synthid_detector.py# SynthID detection
│   │   └── visual_detector.py # Visual pattern analysis
│   ├── learning/
│   │   └── text_detector.py   # Custom ML text detection
│   └── services/              # External API integrations
├── frontend/
│   ├── css/styles.css         # Premium dark theme
│   ├── js/
│   │   ├── app.js             # Main application logic
│   │   ├── gemini-service.js  # API service layer
│   │   └── result-view.js     # Results rendering
│   └── pages/                 # HTML pages
├── veritas_text_detector/     # Trained ML model files
│   ├── model.safetensors      # Model weights (Git LFS)
│   ├── config.json            # Model configuration
│   └── tokenizer.json         # Tokenizer
└── training/                  # Training scripts
```

---

## 🔧 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/detect/ai-text` | POST | Pure AI text detection (ML only) |
| `/api/verify/text` | POST | Fact-checking with ensemble |
| `/api/verify/image` | POST | Image deepfake detection |
| `/api/verify/audio` | POST | Audio analysis |
| `/api/verify/video` | POST | Video forensics |
| `/api/learn` | POST | Submit feedback for learning |
| `/api/health` | GET | Health check |

---

## 📊 How the Trust Score Works

| Score | Verdict | Meaning |
|-------|---------|---------|
| 70-100% | **Authentic** | Very likely real/human-made |
| 31-69% | **Inconclusive** | Mixed signals, manual review needed |
| 0-30% | **AI-Generated** | Likely fake or AI-made |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## ⚠️ Disclaimer

Veritas is an AI-powered tool that provides **probabilistic predictions**, not absolute truth. Always:
- Double-check important findings with other sources
- Don't use as sole evidence for serious decisions
- Consider it a helpful first step, not the final answer

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

**Built with ❤️ by Dhanush Pillay**

</div>
