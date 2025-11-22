import os
import tempfile
import requests
from typing import Optional

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "api_default")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_response_with_gemini(prompt: str, max_tokens: int = 256) -> str:
    """Generates a response using OpenRouter (Gemini)."""
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set.")
        return "I'm sorry, I can't think right now. (Missing API Key)"

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": "https://github.com/HackWestern12_Proj", # Optional
        # "X-Title": "HackWestern12 Project", # Optional
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free", # Using a likely free/available model
        "messages": [
            {"role": "system", "content": "You are a helpful and empathetic therapist. Keep your responses concise (under 2-3 sentences) and supportive."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            print(f"OpenRouter Error: {data}")
            return "I'm having trouble understanding that."
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        return "I'm sorry, I'm having connection issues."

def tts_elevenlabs(text: str, out_path: Optional[str] = None) -> Optional[str]:
    """Simple ElevenLabs TTS stream-to-file. Returns path or None if key missing."""
    if not ELEVEN_API_KEY:
        print("Warning: ELEVENLABS_API_KEY not set.")
        return None

    out_path = out_path or tempfile.mktemp(suffix=".wav")
    # Use the voice ID from env or default
    voice_id = ELEVEN_VOICE_ID or "21m00Tcm4TlvDq8ikWAM" # Default Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
        return out_path
    except Exception as e:
        print(f"Error calling ElevenLabs: {e}")
        return None
