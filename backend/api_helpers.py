import os
import tempfile
import requests
from typing import Optional

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "api_default")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_response_with_gemini(prompt: str, max_tokens: int = 128) -> str:
    """Placeholder Gemini wrapper. Replace with official SDK or your project's auth method.

    Returns a short textual response or empty string if not configured.
    """
    if not GEMINI_API_KEY:
        return ""  # Not configured

    # NOTE: This is a placeholder. Replace with Google Generative API or Gemini HTTP call.
    # The implementation depends on your access method (service account, oauth, etc.).
    # For now, return a fixed echo to allow local testing.
    return f"[gemini placeholder reply to] {prompt[:200]}"

def tts_elevenlabs(text: str, out_path: Optional[str] = None) -> Optional[str]:
    """Simple ElevenLabs TTS stream-to-file. Returns path or None if key missing."""
    if not ELEVEN_API_KEY:
        return None

    out_path = out_path or tempfile.mktemp(suffix=".wav")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "voice_settings": {"stability": 0.6, "similarity_boost": 0.75}}
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
    return out_path
