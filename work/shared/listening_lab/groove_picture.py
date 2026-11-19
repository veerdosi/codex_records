from pathlib import Path
import json
import secrets

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import soundfile as sf

root = Path(__file__).resolve().parent
inputs = [root.parent/'elastic/jk_d2_flash_drums_clean_eight.wav', root/'agent_mix/hybrid_drum_bus.wav']
if secrets.randbelow(2):
    inputs.reverse()
beat = 60/87
fig, axes = plt.subplots(2, 1, figsize=(9.1,3.7), sharex=True, sharey=True, layout='constrained')
fig.suptitle('Low drum energy through two bars', x=.085, ha='left', fontsize=15, fontweight='semibold')
for label, source, ax in zip(('A','B'), inputs, axes):
    y, sr = sf.read(source, frames=round(8*beat*44100), dtype='float32', always_2d=True)
    filtered = signal.sosfiltfilt(signal.butter(3, (35, 115), fs=sr, btype='bandpass', output='sos'), y, axis=0)
    power = np.mean(filtered**2, axis=1)
    size = round(.016*sr)
    energy = np.sqrt(np.maximum(0,signal.fftconvolve(power,np.ones(size)/size,mode='same')))
    energy /= np.percentile(energy,99)
    positions = np.arange(len(energy))/sr/beat
    for i in range(16):
        ax.axvline(i/2, color=('#9da9b7' if i%2==0 else '#dce2e9'), lw=.8, zorder=0)
    ax.plot(positions[::32], energy[::32], color=('#2646a9' if label=='A' else '#8b3864'), lw=1.3)
    ax.set_ylabel(f'Clip {label}')
    ax.set(xlim=(0,8), ylim=(0,1.55), yticks=(0,1))
    ax.spines[['top','right']].set_visible(False)
axes[-1].set_xticks(np.arange(0,8,.5), [str(1+i//2) if i%2==0 else '&' for i in range(16)])
axes[-1].set_xlabel('Beat grid at 87 BPM ( & marks the halfway point )')
fig.savefig(root/'blind_groove.png', dpi=155)
(root/'blind_groove_key.json').write_text(json.dumps({label:source.name for label,source in zip(('A','B'),inputs)},indent=2))
