import os
import sys
import numpy as np
import soundfile as sf
import requests

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
os.makedirs(OUT_DIR, exist_ok=True)
wav_path = os.path.join(OUT_DIR, 'tmp_smoke.wav')
# 1s 16kHz mono sine at 440Hz
sr = 16000
t = np.linspace(0, 1, int(sr*1), endpoint=False)
wave = 0.1 * np.sin(2 * np.pi * 440 * t)
sf.write(wav_path, wave, sr, subtype='PCM_16')

url = 'http://127.0.0.1:5000/api/analyze'
print('Posting', wav_path, 'to', url)
try:
    with open(wav_path, 'rb') as f:
        files = {'file': ('tmp_smoke.wav', f, 'audio/wav')}
        resp = requests.post(url, files=files, timeout=300)
    print('Status code:', resp.status_code)
    try:
        print('Response JSON:')
        print(resp.json())
    except Exception:
        print('Response text:')
        print(resp.text)
except Exception as e:
    print('Error during request:', e)
    sys.exit(2)

# print a small confirmation about GPU visibility from inside venv as well
try:
    import torch
    print('torch.__version__=', torch.__version__)
    print('torch.version.cuda=', torch.version.cuda)
    print('torch.cuda.is_available=', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('torch.cuda.device_count=', torch.cuda.device_count())
except Exception as e:
    print('Could not import torch in script:', e)
