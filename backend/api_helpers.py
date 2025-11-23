import os
import tempfile
import requests
from typing import Optional

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "api_default")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Allow overriding model name via env; default to a known OpenRouter preview model
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")


def _synthesize_local_reply(transcript: str, emotions: dict | None) -> str:
    """Create a short empathetic reply locally when the model returns only reasoning.

    This avoids exposing the model's chain-of-thought to the user and guarantees
    the frontend receives a caring response.
    """
    # Choose dominant emotion if available
    dominant = None
    if emotions:
        try:
            dominant = max(emotions.items(), key=lambda kv: kv[1])[0]
        except Exception:
            dominant = None

    # Therapist-style templates keyed by emotion. They validate feelings,
    # offer brief support, and invite a gentle follow-up without parroting.
    templates = {
        "angry": (
            "I can hear how upset you are — that sounds really frustrating. "
            "If you want, tell me what would help right now; I'm listening."
        ),
        "disgust": (
            "That sounds upsetting and unfair. I'm sorry you had to go through that. "
            "Would you like to share more about how it affected you?"
        ),
        "fearful": (
            "That must have felt frightening — it's natural to feel shaken. "
            "Are you safe now, and do you want to talk about what helped afterward?"
        ),
        "happy": (
            "It's nice to hear moments of joy — I'm glad that happened for you. "
            "Want to tell me more about what made it feel good?"
        ),
        "neutral": (
            "Thanks for sharing that. I hear you. "
            "How are you feeling about it now?"
        ),
        "sad": (
            "I'm really sorry you're feeling sad — that sounds painful. "
            "If you'd like, tell me what's been hardest about it."
        ),
        "surprised": (
            "That sounds surprising and unsettling — I can see why it stood out. "
            "Do you want to say more about how it affected you?"
        ),
    }

    # Choose template for dominant emotion, fallback to a neutral supportive line
    reply = templates.get(dominant)
    if not reply:
        reply = (
            "Thank you for sharing. I hear you and I'm here to listen. "
            "Would you like to say more about how you're feeling?"
        )

    # If there's no dominant emotion but a transcript suggests immediate risk,
    # include a brief safety-check (best-effort heuristic)
    lower = (transcript or "").lower()
    if any(w in lower for w in ("hurt myself", "kill myself", "want to die", "not want to live", "suicide")):
        return (
            "I'm really sorry you're feeling that way. If you're in immediate danger, please contact local emergency services or a crisis line. "
            "If you'd like, tell me what's going on and I'll listen."
        )

    return reply[:400]

def generate_response_with_gemini(
    transcript: str,
    emotions: dict | None = None,
    history: list | None = None,
    max_tokens: int = 256,
) -> str:
    """Generates an empathetic response using OpenRouter (Gemini).

    Accepts `transcript`, optional `emotions` mapping (label -> score), and an
    optional `history` (list of {role, content}). The history is included so
    the model keeps conversational context (we cap to recent messages).
    The system prompt instructs the model to treat emotion estimates as
    probabilistic and to NOT reveal internal chain-of-thought.
    """
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set.")
        return "I'm sorry, I can't think right now. (Missing API Key)"

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Build emotion lines in a consistent, sorted order (top-first)
    emotion_lines = ""
    if emotions:
        try:
            # Sort emotions by score desc and include top 5
            items = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)[:5]
            emotion_lines = "\nEmotion estimates (probabilistic):\n" + "\n".join([
                f"- {k}: {v:.3f}" for k, v in items
            ])
        except Exception:
            emotion_lines = "\nEmotion estimates: (unavailable)"

    # User-visible content: transcript + emotion estimates (explicitly framed)
    user_content = (
        f"Transcript: {transcript}\n\n"
        f"Please respond as a short, empathetic therapist (1-3 sentences)."
        f" Treat the emotion estimates below as probabilistic — do not assert them as facts; instead, validate feelings and ask a clarifying question when appropriate."
        + emotion_lines
    )

    # System prompt: explicitly instruct about chain-of-thought and emotion handling
    system_prompt = (
        "You are a helpful and empathetic therapist. Keep responses concise and supportive. "
        "Do NOT reveal internal chain-of-thought or reasoning. Treat emotion estimates as probabilistic signals only — do not state them as facts. "
        "When unsure, ask a brief clarifying question."
    )

    # Start building messages: include system prompt, then recent history (if any), then the current user content
    messages = [{"role": "system", "content": system_prompt}]
    if history and isinstance(history, list):
        try:
            # Cap history to the last 20 entries
            for h in history[-20:]:
                role = h.get("role", "user") if isinstance(h, dict) else "user"
                content = h.get("content", "") if isinstance(h, dict) else str(h)
                # Normalize role names (openrouter expects 'user'/'assistant')
                messages.append({"role": role, "content": content})
        except Exception:
            pass

    messages.append({"role": "user", "content": user_content})

    payload = {"model": OPENROUTER_MODEL, "messages": messages, "max_tokens": max_tokens}

    r = None
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            # Try several common locations for returned assistant text
            text = None
            # 1) OpenRouter normalized shape: choice['message']['content'] may be string or dict
            msg = choice.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, dict):
                    # nested forms: try common keys
                    text = content.get("text") or content.get("content")
            # 2) Older OpenAI-like shape: choice.get('text')
            if not text:
                text = choice.get("text")
            # 3) Some providers include 'message' as a plain string
            if not text and isinstance(msg, str):
                text = msg

            # If still no text, do a safe follow-up request asking for a concise
            # empathetic reply based only on the transcript+emotions. Do NOT
            # expose or return the model's internal chain-of-thought or reasoning.
            if not text:
                try:
                    follow_payload = {
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a helpful and empathetic therapist. Do NOT reveal your internal chain-of-thought or reasoning. Provide a concise, caring reply in 1-3 sentences."},
                            {"role": "user", "content": user_content},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    }
                    r2 = requests.post(url, json=follow_payload, headers=headers, timeout=20)
                    r2.raise_for_status()
                    d2 = r2.json()
                    if "choices" in d2 and len(d2["choices"]) > 0:
                        choice2 = d2["choices"][0]
                        msg2 = choice2.get("message")
                        # Try to extract text from the follow-up response
                        if isinstance(msg2, dict):
                            content2 = msg2.get("content")
                            if isinstance(content2, str) and content2.strip():
                                return content2.strip()
                            if isinstance(content2, dict):
                                text2 = content2.get("text") or content2.get("content")
                                if text2:
                                    return str(text2).strip()
                        # Fallback to older shape
                        if choice2.get("text"):
                            return str(choice2.get("text")).strip()
                    # If follow-up didn't produce text, try to extract reasoning and
                    # synthesize a safe local reply so we don't expose chain-of-thought.
                    reasoning_text = None
                    try:
                        if isinstance(choice2.get("message"), dict):
                            reasoning_text = choice2["message"].get("reasoning")
                        if not reasoning_text:
                            rd = choice2.get("message", {}).get("reasoning_details") or choice2.get("reasoning_details")
                            if rd and isinstance(rd, list) and len(rd) > 0:
                                first = rd[0]
                                if isinstance(first, dict):
                                    reasoning_text = first.get("text") or first.get("content")
                                elif isinstance(first, str):
                                    reasoning_text = first
                    except Exception:
                        reasoning_text = None

                    if reasoning_text:
                        # Use local synthesizer based on original transcript+emotions
                        return _synthesize_local_reply(transcript, emotions)

                    # As a last resort, log both responses for debugging and return empty
                    print("OpenRouter initial response (no assistant text):")
                    print(data)
                    print("OpenRouter follow-up response:")
                    try:
                        print(d2)
                    except Exception:
                        pass
                    return ""
                except Exception as e:
                    print(f"Error doing follow-up OpenRouter request: {e}")
                    print("Initial response was:")
                    print(data)
                    return ""

            return (text or "").strip()
        else:
            print(f"OpenRouter Error (no choices): {data}")
            return "I'm having trouble understanding that."
    except requests.HTTPError as e:
        # If OpenRouter returned a 400, include the body for diagnosis
        body = None
        try:
            body = r.text if r is not None else None
        except Exception:
            body = None
        print(f"Error calling OpenRouter: {e}; response body: {body}")
        return "I'm sorry, I'm having connection issues."
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        return "I'm sorry, I'm having connection issues."

def tts_elevenlabs(text: str, out_path: Optional[str] = None) -> Optional[str]:
    """Simple ElevenLabs TTS stream-to-file. Returns path or None if key missing."""
    if not ELEVEN_API_KEY:
        print("Warning: ELEVENLABS_API_KEY not set.")
        return None
    # Save TTS output into the project root so the frontend can request it by basename.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(project_root, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(suffix=".wav", dir=project_root)
    os.close(fd)

    # Use the voice ID from env or default
    voice_id = ELEVEN_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"  # Default Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
        # Return only the basename so the frontend can request `/api/tts-file/<basename>`.
        return os.path.basename(tmp_path)
    except Exception as e:
        print(f"Error calling ElevenLabs: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return None
