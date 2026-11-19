"""Separate the return passage and a bar-aligned reference from before the lift."""
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

stage = Path(__file__).resolve().parent
root = stage.parents[4]
media = root / 'reaper/Go Back to the Part Where I Leave/Media'
sr = 44100
origin = 16.551088435374
start, end = 126.8, 135.6
bar = 240 / 87

def read(name, a, b):
    audio, rate = sf.read(
        media / name, start=round((a-origin)*sr),
        frames=round((b-a)*sr), dtype='float32',
    )
    assert rate == sr
    return audio

current = read('Runaway - softened return attack.wav', start, end)
reference = read('Runaway - extended handoffs.wav', start-bar, end-bar)
model = get_model('htdemucs_ft').eval()
torch.set_num_threads(5)
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
with torch.inference_mode():
    audio = torch.from_numpy(np.stack([current, reference]).transpose(0, 2, 1).copy())
    try:
        stems = apply_model(model, audio, shifts=0, overlap=.5, device=device)
    except (RuntimeError, NotImplementedError):
        stems = apply_model(model, audio, shifts=0, overlap=.5, device='cpu')
np.savez(stage/'Stems around return.npz', stems=stems.cpu().numpy().transpose(0,1,3,2), start=start)
