# real_time_emotion_server.py
import threading
import queue
import torch
import librosa
import numpy as np
from emotion_model import EmotionDetector
import soundfile as sf

detector = EmotionDetector(device="cuda")
audio_queue = queue.Queue()

def worker():
    while True:
        item = audio_queue.get()
        if item is None:
            break
        audio_array, sr, callback = item

        # Resample to Whisper's required SR
        if sr != detector.target_sr:
            import torchaudio
            audio_tensor = torch.tensor(audio_array).unsqueeze(0)
            audio_tensor = torchaudio.functional.resample(audio_tensor, sr, detector.target_sr)
            audio_array = audio_tensor.squeeze().cpu().numpy()

        temp_path = "temp_real_time_audio.wav"
        sf.write(temp_path, audio_array, detector.target_sr)


        results = detector.predict(temp_path)
        top = max(results, key=results.get)
        callback(results, top)

        audio_queue.task_done()

thread = threading.Thread(target=worker, daemon=True)
thread.start()

def submit_audio(audio_array, sr, callback):
    audio_queue.put((audio_array, sr, callback))

# Example mic loop
if __name__ == "__main__":
    import sounddevice as sd

    def print_results(results, top):
        print("\nEmotion detected:")
        for label, score in results.items():
            print(f"{label:10s}: {score:.4f}")
        print(f"🔥 Dominant Emotion: {top}")

    samplerate = 16000
    duration = 3

    print("[INFO] Starting mic...")

    while True:
        chunk = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
        sd.wait()
        submit_audio(chunk.squeeze(), samplerate, print_results)
