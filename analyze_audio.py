from emotion_model import EmotionDetector
import sys
import time

if len(sys.argv) < 2:
    print("Usage: python analyze_audio.py path/to/audio.wav")
    exit()

audio_path = sys.argv[1]

detector = EmotionDetector()

start = time.time()
results = detector.predict(audio_path)
elapsed = time.time() - start

print("\n=== Emotion Probabilities ===")
for label, score in results.items():
    print(f"{label:10s}: {score:.4f}")

top_emotion = max(results, key=results.get)
print("\n🔥 Dominant Emotion:", top_emotion)
print(f"⏱️ Analysis Time: {elapsed:.2f} seconds")
