import threading
import queue
from emotion_model import EmotionDetector

detector = EmotionDetector(device="cuda")
audio_queue = queue.Queue()

def worker():
    while True:
        item = audio_queue.get()
        if item is None:
            break
        audio_path, callback = item
        results = detector.predict(audio_path)
        top = max(results, key=results.get)
        callback(audio_path, results, top)
        audio_queue.task_done()

thread = threading.Thread(target=worker, daemon=True)
thread.start()

def submit_audio(audio_path, callback):
    audio_queue.put((audio_path, callback))

def print_results(audio_path, results, top):
    print(f"\nProcessed: {audio_path}")
    for k, v in results.items():
        print(f"{k:10s}: {v:.4f}")
    print(f"🔥 Dominant Emotion: {top}")

if __name__ == "__main__":
    submit_audio("samples/test.wav", print_results)
    submit_audio("samples/test2.wav", print_results)

    audio_queue.join()
    audio_queue.put(None)
    thread.join()
