from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import tempfile

# Ensure project root is on sys.path so imports like `emotion_model` resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from emotion_model import EmotionDetector
from api_helpers import generate_response_with_gemini, tts_elevenlabs, _synthesize_local_reply
import json

app = Flask(__name__)
CORS(app)

# Lazy-loaded detector to speed startup
_detector = None

def get_detector():
    global _detector
    if _detector is None:
        device = os.getenv("DEVICE")
        _detector = EmotionDetector(device=device)  # uses existing emotion_model
    return _detector

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Accept multipart/form-data with key 'audio' (wav). Returns emotion probs and optional LM/TTS results."""
    if "audio" not in request.files:
        return jsonify({"error": "no audio file provided"}), 400

    f = request.files["audio"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        f.save(tmp.name)
        detector = get_detector()
        emotions = detector.predict(tmp.name)

        response = {"emotions": emotions}

        # Optional: if a `do_chat` flag is present, call Gemini placeholder and TTS
        do_chat = request.form.get("do_chat", "false").lower() in ("1", "true", "yes")
        # Optional history (JSON string) containing previous messages
        history_raw = request.form.get("history")
        history = None
        if history_raw:
            try:
                history = json.loads(history_raw)
            except Exception:
                history = None
        if do_chat:
            # Use a crude local STT placeholder: if client provided transcript use it
            transcript = request.form.get("transcript", "")
            if not transcript:
                transcript = ""  # could integrate local STT here

            if transcript:
                # If the user asks an explicit memory question, answer locally
                # from the supplied `history` to avoid relying on the LM.
                t_lower = transcript.lower()
                memory_triggers = ["do you remember", "where did i", "where was i", "did i get shot", "where did i get shot", "where was i shot", "remember where"]
                if any(tok in t_lower for tok in memory_triggers):
                    lm_reply = _synthesize_local_reply(transcript, emotions, history=history)
                else:
                    # Pass transcript, emotions, and optional history to the LM helper.
                    lm_reply = generate_response_with_gemini(transcript, emotions, history=history, max_tokens=256)
                response["transcript"] = transcript
                response["reply_text"] = lm_reply
                tts_path = tts_elevenlabs(lm_reply) if lm_reply else None
                response["reply_audio_path"] = os.path.basename(tts_path) if tts_path else None
            else:
                response["reply_text"] = ""

        return jsonify(response)
    finally:
        # Remove the temporary uploaded audio file as it's no longer needed
        try:
            tmp.close()
        except Exception:
            pass
        try:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
        except Exception:
            pass

@app.route("/api/tts-file/<filename>", methods=["GET"])
def tts_file(filename):
    # Serve file from current working directory if exists (used for returned ElevenLabs file)
    # Build path relative to project root so files saved by `api_helpers.tts_elevenlabs`
    # (which saves into the project root) are served correctly by basename.
    path = os.path.abspath(os.path.join(ROOT, filename))
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, mimetype="audio/wav")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


@app.route("/api/cleanup", methods=["POST"])
def cleanup_files():
    """Delete temporary audio files by basename supplied in JSON {"files": ["a.wav"]}.

    Only allows basenames (no paths) and deletes files from project root for safety.
    """
    try:
        data = request.get_json(force=True)
        files = data.get("files") if isinstance(data, dict) else None
        if not files or not isinstance(files, list):
            return jsonify({"deleted": [], "error": "invalid payload"}), 400

        deleted = []
        for name in files:
            if not isinstance(name, str):
                continue
            # Prevent path traversal
            if os.path.basename(name) != name:
                continue
            path = os.path.abspath(os.path.join(ROOT, name))
            # Ensure file is inside project root
            if not path.startswith(os.path.abspath(ROOT)):
                continue
            try:
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(name)
            except Exception:
                pass

        return jsonify({"deleted": deleted})
    except Exception as e:
        return jsonify({"deleted": [], "error": str(e)}), 500
