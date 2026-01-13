# VERITAS - AI-Powered Media Verification System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-red?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Detect deepfakes, AI-generated content, and misinformation with advanced AI forensics.**

</div>

---

## Features

### AI Text Detection
- Custom-trained DistilBERT model for AI vs human text classification
- Ensemble system combining ML model (60%) with LLM analysis (40%)
- Dedicated endpoint for fast, ML-only detection

### Fact Checking
- Claim verification using web search and AI reasoning
- Source finding and cross-referencing
- Powered by Groq's LLaMA 4

### Image Analysis
- AI-generated image detection
- Error Level Analysis (ELA) forensics
- C2PA and SynthID watermark detection
- Reverse image search integration

### Video Forensics
- Frame-by-frame deepfake detection
- Lip-sync analysis
- Face manipulation detection

### Audio Analysis
- Voice cloning detection
- Speech-to-text transcription via Whisper
- Audio splicing identification

---

## Architecture

```
+-------------------------------------------------------------+
|                      FRONTEND (Vanilla JS)                  |
|  +----------+ +------------+ +-------+ +-------+ +-------+  |
|  |AI Detect | | Fact Check | | Image | | Audio | | Video |  |
|  +----+-----+ +-----+------+ +---+---+ +---+---+ +---+---+  |
+-------|-------------|------------|---------|---------|------+
        |             |            |         |         |
        v             v            v         v         v
+-------------------------------------------------------------+
|                   FLASK BACKEND (Python)                    |
|                                                             |
|  +-------------------------------------------------------+  |
|  |              API ENDPOINTS                            |  |
|  |  /api/detect/ai-text  ->  ML Model Only (Fast)        |  |
|  |  /api/verify/text     ->  Ensemble (ML + Groq)        |  |
|  |  /api/verify/image    ->  Forensics + Groq            |  |
|  |  /api/verify/audio    ->  Whisper + Analysis          |  |
|  |  /api/verify/video    ->  Frame Analysis + Groq       |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +---------------+  +---------------+  +----------------+   |
|  | Custom Model  |  |   Groq API    |  |   Forensics    |   |
|  | (DistilBERT)  |  |   (LLaMA 4)   |  |   (ELA, C2PA)  |   |
|  | Local         |  |   Remote      |  |   Local        |   |
|  +---------------+  +---------------+  +----------------+   |
+-------------------------------------------------------------+
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Groq API Key (available at console.groq.com)

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

Access the application at `http://localhost:5000`

---

## ML Models

### Custom-Trained Model
| Model | Base | Dataset | Purpose |
|-------|------|---------|---------|
| veritas_text_detector | DistilBERT | ai-text-detection-pile | AI vs Human text classification |

### Groq API Models
| Model | Purpose |
|-------|---------|
| LLaMA 4 Scout 17B | Text and image reasoning |
| Whisper Large v3 Turbo | Audio transcription |

---

## Project Structure

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
│   ├── css/styles.css         # UI styling
│   ├── js/
│   │   ├── app.js             # Main application logic
│   │   ├── gemini-service.js  # API service layer
│   │   └── result-view.js     # Results rendering
│   └── pages/                 # HTML pages
├── veritas_text_detector/     # Trained ML model files
│   ├── model.safetensors      # Model weights
│   ├── config.json            # Model configuration
│   └── tokenizer.json         # Tokenizer
└── training/                  # Training scripts
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/detect/ai-text` | POST | ML-only AI text detection |
| `/api/verify/text` | POST | Ensemble fact-checking |
| `/api/verify/image` | POST | Image deepfake detection |
| `/api/verify/audio` | POST | Audio analysis |
| `/api/verify/video` | POST | Video forensics |
| `/api/learn` | POST | Submit feedback for learning |
| `/api/health` | GET | Health check |

---

## Trust Score

| Score | Verdict | Interpretation |
|-------|---------|----------------|
| 70-100% | Authentic | High probability of genuine content |
| 31-69% | Inconclusive | Mixed signals, manual review recommended |
| 0-30% | AI-Generated | High probability of synthetic content |

---

## Disclaimer

Veritas provides probabilistic predictions based on AI analysis. Results should not be used as sole evidence for critical decisions. Always verify important findings through additional sources.

---

## License

MIT License

---

**Developed by Dhanush Pillay**
