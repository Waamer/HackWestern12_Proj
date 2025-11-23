from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from emotion_model import EmotionDetector
from api_helpers import generate_response_with_gemini, tts_elevenlabs

app = Flask(__name__)
CORS(app)


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

        do_chat = request.form.get("do_chat", "false").lower() in ("1", "true", "yes")
        if do_chat:
            transcript = request.form.get("transcript", "")
            if not transcript:
                transcript = ""

            if transcript:
                prompt = f"User: {transcript}\nAssistant:" 
                lm_reply = generate_response_with_gemini(prompt)
                response["transcript"] = transcript
                response["reply_text"] = lm_reply
                tts_path = tts_elevenlabs(lm_reply) if lm_reply else None
                response["reply_audio_path"] = os.path.basename(tts_path) if tts_path else None
            else:
                response["reply_text"] = ""

        return jsonify(response)
    finally:
        try:
            tmp.close()
        except Exception:
            pass

@app.route("/api/tts-file/<filename>", methods=["GET"])
def tts_file(filename):
    path = os.path.abspath(filename)
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, mimetype="audio/wav")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
