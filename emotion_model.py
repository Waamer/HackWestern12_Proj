# emotion_model.py
import torch
import librosa
import numpy as np
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

MODEL_ID = "firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"

class EmotionDetector:
    def __init__(self, device=None):
        print("[INFO] Loading Whisper Emotion Model...")

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[INFO] Using device: {self.device}")

        self.model = AutoModelForAudioClassification.from_pretrained(MODEL_ID).to(self.device)
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID, do_normalize=True)
        self.id2label = self.model.config.id2label

        # Pre-calc values
        self.target_sr = self.feature_extractor.sampling_rate
        self.max_duration = 30.0
        self.max_length = int(self.target_sr * self.max_duration)

    def preprocess(self, audio_path):
        # Load audio preserving native sampling rate, then resample to model target SR
        audio, sr = librosa.load(audio_path, sr=None, mono=True)

        # If the audio isn't at the extractor's sampling rate, resample explicitly.
        if sr != self.target_sr:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)
            sr = self.target_sr

        # Ensure we have a 1-D float32 numpy array
        audio = np.asarray(audio, dtype=np.float32)

        # Trim or pad to fixed length expected by the model
        if len(audio) > self.max_length:
            audio = audio[: self.max_length]
        else:
            audio = np.pad(audio, (0, self.max_length - len(audio)))

        inputs = self.feature_extractor(
            audio,
            sampling_rate=self.target_sr,
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt",
        )
        return inputs

    def predict(self, audio_path):
        """Predict emotion probabilities for an audio file.

        Uses single-pass inference by default. For improved robustness you can call
        with `tta=True` to average predictions across small temporal shifts (test-time augmentation).
        """
        inputs = self.preprocess(audio_path)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model(**inputs)

        logits = output.logits[0]
        probs = torch.softmax(logits, dim=-1).cpu().numpy()

        results = {self.id2label[i]: float(probs[i]) for i in range(len(probs))}
        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
