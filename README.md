<div align="center">
  <hr>
  
  <h1>🎙️ Echoes</h1>
  
  <hr>
  <h3 align="center">
    Where your voice finds understanding, and understanding finds you. <br><br>
    <img src="https://img.shields.io/badge/Powered%20by-Whisper-blue" height="24">
    <img src="https://img.shields.io/badge/Powered%20by-Gemini-orange" height="24">
    <img src="https://img.shields.io/badge/Powered%20by-ElevenLabs-purple" height="24">
    <img src="https://img.shields.io/badge/Built%20with-React-cyan" height="24">
    <img src="https://img.shields.io/badge/Version-1.0-darkblue" height="24">
  </h3>
</div>

---

## 📌 Overview

**Echoes** is a real-time emotion-aware mental health companion that analyzes both **what you say** and **how you say it** to provide empathetic, context-aware support. The system combines speech-to-text transcription, emotion detection from voice patterns, AI-powered conversational therapy, and natural voice responses to create a compassionate digital therapist that truly listens.

Unlike text-only chatbots, Echoes captures emotional nuance in your voice—detecting stress, fear, sadness even when words seem neutral—and responds with understanding tailored to both your words and your feelings.

---

## ✨ Features

- 🎤 **Real-time Voice Analysis** - GPU-accelerated emotion detection from voice tone and patterns
- 🧠 **7 Emotion Recognition** - Detects happy, sad, angry, fearful, disgusted, surprised, and neutral states
- 💬 **Context-Aware Responses** - Prioritizes what you say with emotion as supplementary context
- 🎯 **Three Response Modes**:
  - **Empathetic Listening** - Validates feelings and explores concerns
  - **Actionable Advice** - Provides 2-4 specific steps tailored to your situation
  - **Conversational Memory** - Recalls past discussions and context
- 🔄 **Mismatch Detection** - Identifies when emotions and words don't align
- 🗣️ **Text-to-Speech Responses** - Natural voice replies via ElevenLabs
- 💾 **Persistent History** - Remembers conversations across sessions
- ⚡ **Low Latency** - CUDA-optimized processing for near-instant responses

---

## 🎯 Why EmotiVoice?

### The Mental Health Crisis
- **1 in 5 adults** experience mental illness annually
- **Average wait time** for therapy: 2-3 months
- **Cost barrier**: $100-250 per session without insurance
- **Stigma** prevents many from seeking help

### How EmotiVoice Helps
- ✅ **Immediate 24/7 support** - No waiting lists or appointments
- ✅ **Emotion-aware responses** - Understands stress/fear in your voice even when you say "I'm fine"
- ✅ **Judgment-free space** - Complete privacy and confidentiality
- ✅ **Actionable guidance** - Practical advice tailored to your unique situation
- ✅ **Crisis detection** - Recognizes urgent situations and recommends professional help

> **Note:** EmotiVoice is a supportive companion, not a replacement for professional therapy. For serious mental health concerns, please consult a licensed professional.


---

## 📦 Installation

### Prerequisites

- **Windows** with NVIDIA RTX GPU and drivers installed
- **Python 3.10+** (3.11/3.12 recommended)
- **Node.js v18+** and npm
- **Git**
- **PowerShell** (default Windows shell)

### Verify GPU Setup

```powershell
# Shows GPU and driver
nvidia-smi
```

If `nvidia-smi` is not found, install NVIDIA drivers from the NVIDIA website. You do not need full CUDA toolkit installed - only a matching driver is required for PyTorch.

### Clone Repository

```powershell
git clone https://github.com/Waamer/HackWestern12_Proj.git
cd HackWestern12_Proj
```

### Backend Setup

Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
```

### Install PyTorch + torchaudio (GPU)

If you have an NVIDIA RTX and want GPU acceleration, install the matching wheels. Example for CUDA 12.1 (the environment used when developing this repo):

```powershell
python -m pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

If you do NOT have a GPU or prefer CPU-only, use the CPU wheel instead:

```powershell
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Install the rest of the Python dependencies

We added a pinned `requirements.txt` at the repo root that contains the packages from the environment used to develop and test this project. To reproduce the same environment exactly, run:

```powershell
pip install -r requirements.txt
```

If you prefer a smaller, flexible set for the backend only, install the backend minimal list (less reproducible):

```powershell
pip install -r backend/requirements.txt
```

Note: `requirements.txt` at the repo root includes GPU-specific `torch` and `torchaudio` wheels as pinned versions. If you switch CUDA versions, edit or reinstall the appropriate torch wheel.

---

## Frontend setup (Vite + React + TypeScript)

Install Node dependencies from the `frontend` folder:

```powershell
cd frontend
npm install
```

Start the frontend dev server:

```powershell
npm run dev
# Open the Local URL shown by Vite (usually http://localhost:5173)
```

---

## Environment variables / API keys

Create `backend/.env` (copy from `.env.example`) and add keys if you plan to enable Gemini or ElevenLabs features. The project will run without these keys but the LM/TTS features will be disabled.

Variables used (example):

```
GEMINI_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
DEVICE=   # optional: "cuda" or "cpu"
```

Never commit real API keys to git.

---

## Run the backend (Flask)

From the repo root (venv must be activated):

```powershell
& ".\.venv\Scripts\Activate.ps1"
cd "C:\Users\<you>\Documents\Western\Year 4\Hackathon\TEST\backend"
python app.py
```

The backend will run on `http://127.0.0.1:5000` (Flask dev server). Keep this running while you use the frontend.

## Use the frontend UI

- Open the Vite URL (http://localhost:5173) in your browser.
- Click `Start`, speak, then click `Stop`. The frontend encodes WAV client-side and sends it to `POST /api/analyze`.
- The backend returns emotion probabilities which the UI displays.

---

## Optional: Real-time mic script (console)

This repo also includes a console mic loop (`real_time_emotion_server.py`) that captures short chunks with `sounddevice` and runs local emotion detection. To run it (venv active):

```powershell
python real_time_emotion_server.py
```

This will print emotion probabilities to the console for each chunk.

Notes:
- The script tries to use CUDA if available.
- If you see `KeyboardInterrupt` traces when stopping, that is because the script is blocking on `sounddevice.wait()`; use Ctrl-C, or we can add graceful shutdown handling.

---

## Reproducing model behavior & accuracy notes

- The emotion model is loaded from Hugging Face (`firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3`) at runtime. The first load downloads weights and may take time and disk space.
- For consistent accuracy:
  - Ensure audio sample rate and channels are correct (the backend resamples to the model's required sampling rate).
  - Use the pinned `torch`/`torchaudio` wheel that matches your GPU's CUDA version.
  - For noisy or short audio, consider running sliding-window averaging or test-time augmentation — the repo includes `emotion_model.py` which now resamples audio correctly; you can enable TTA or windowing for improved stability.

---

## Troubleshooting

- `ModuleNotFoundError: No module named 'emotion_model'` when running `backend/app.py`:
  - Ensure you run `python backend/app.py` from the repository root and that `.venv` is activated. `backend/app.py` inserts the project root into `sys.path` automatically.

- `Import 'torchaudio' could not be resolved` or runtime import errors:
  - Make sure you installed the CUDA-matching `torchaudio` wheel shown in the PyTorch commands above.

- `sounddevice` errors for microphone:
  - Install `sounddevice` (already in our pinned `requirements.txt`) and verify the microphone is available. Use Windows privacy settings to allow microphone access.

- Frontend Start/Stop does nothing in the browser:
  - Ensure you opened the Vite URL and the backend is running at `http://localhost:5000`.
  - Browser may block getUserMedia — allow microphone permission when the browser asks.

---

## Optional: Add Git LFS for model files

If you plan to commit model artifacts (not recommended), enable Git LFS and track large files:

```powershell
git lfs install
git lfs track "*.safetensors"
git add .gitattributes
```

---

## Development tips
- Use `requirements.txt` at the repo root for exact reproducibility.
- Use `backend/requirements.txt` only for a small flexible install (not pinned).
- For production deployment replace the Flask dev server with a WSGI production server (Gunicorn/uvicorn) and consider a reverse proxy.

---

If you want, I can also:
- Add a `start-dev.ps1` that opens two PowerShell windows for backend and frontend.
- Add an `evaluate.py` helper to measure accuracy over a labeled folder of audio.
- Add a small script to automate selecting and installing the correct PyTorch wheel for the detected GPU/CUDA.

Tell me which of those you'd like next.
