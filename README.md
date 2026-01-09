# Veritas - AI Media Verification & Forensics Platform

**Veritas** is an advanced media forensics system designed to detect deepfakes, AI-generated content, and disinformation. Powered by Google's **Gemini 2.0 Flash** and custom-trained models, it provides real-time verification across text, image, audio, and video formats.

![Veritas](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Key Features

### Multimodal Forensic Analysis
- **📄 Text Verification**: LLM fingerprinting, fact-checking, logical consistency analysis
- **🖼️ Image Forensics**: Error Level Analysis, generative artifact detection, EXIF inspection
- **🎙️ Audio Analysis**: Spectral anomaly detection, voice cloning detection, splicing analysis
- **🎥 Video Deepfake Detection**: Temporal consistency, lip-sync analysis, lighting physics

### Live Web Provenance
- Reverse image search integration
- Context verification via Google Search grounding
- Source attribution and fact-check cross-referencing

### AI Learning System
- User feedback loop for continuous improvement
- Pattern learning from verified corrections
- Supabase-backed pattern storage

---

## 📁 Project Structure

```
Veritas/
├── index.html                 # Main entry point
├── frontend/
│   ├── pages/
│   │   ├── scanning.html      # Analysis loading screen
│   │   └── results.html       # Results display
│   ├── css/styles.css         # Styling
│   └── js/
│       ├── shared.js          # Common utilities
│       └── icons.js           # SVG icons
├── backend/
│   ├── app.py                 # Flask API server
│   ├── config.py              # Configuration
│   ├── forensics/             # Image forensics modules
│   ├── services/              # External API integrations
│   └── learning/              # AI learning system
└── training/
    ├── train_deepfake.py      # Local training script
    ├── train_colab.py         # Google Colab training
    └── requirements.txt       # Training dependencies
```

---

## �️ Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js (optional, for development)
- Google AI Studio API Key
- Groq API Key (for AI analysis)

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GROQ_API_KEY=your_key_here" > .env
echo "GOOGLE_API_KEY=your_key_here" >> .env

# Run server
python app.py
```

### Frontend
Simply open `index.html` in your browser, or serve with:
```bash
python -m http.server 8000
```

---

## 🧠 Model Training

Veritas includes a custom deepfake detection model trained on the [Deepfake-vs-Real-60K](https://huggingface.co/datasets/prithivMLmods/Deepfake-vs-Real-60K) dataset.

### Option 1: Google Colab (Recommended)
1. Open [Google Colab](https://colab.research.google.com)
2. Upload `training/train_colab.py`
3. Enable GPU: Runtime → Change runtime type → GPU
4. Run the notebook
5. Model saves to your Google Drive

### Option 2: Local Training
```bash
cd training
pip install -r requirements.txt
python train_deepfake.py
```

**Note**: Local training requires a GPU for reasonable performance. CPU training will be very slow.

---

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/verify/text` | POST | Analyze text for AI generation |
| `/api/verify/image` | POST | Analyze image for manipulation |
| `/api/verify/audio` | POST | Analyze audio for voice cloning |
| `/api/verify/video` | POST | Analyze video for deepfakes |
| `/api/learn` | POST | Submit feedback for AI learning |
| `/api/health` | GET | Health check |

---

## ⚠️ Disclaimer

Veritas uses AI-based probabilistic analysis. It may produce false positives or negatives. **Do not** use as the sole basis for legal or critical decisions. Always corroborate findings with traditional forensic tools and human judgment.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

*Built with Flask, Gemini AI, and HuggingFace Transformers*