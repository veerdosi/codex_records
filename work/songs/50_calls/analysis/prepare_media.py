from pathlib import Path
import shutil
import sys
import numpy as np
import soundfile as sf

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parents[1] / 'shared'))
from dsp import SR, load, filt

media = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls/Media'
media.mkdir(parents=True, exist_ok=True)
demucs = root / 'stems/demucs/htdemucs'

def save(name, audio):
    sf.write(media / name, audio, SR, subtype='PCM_24')

for name, folder in [('Hook', 'juice_first'), ('Verse', 'juice_verse_bed')]:
    for role, stem in [('Drums', 'drums'), ('Bass', 'bass'), ('Guitar', 'other')]:
        shutil.copyfile(demucs / folder / f'{stem}.wav', media / f'{name}-{role}.wav')

shutil.copyfile(demucs / 'juice_first/vocals.wav', media / 'Juice-hook.wav')
shutil.copyfile(root / 'stems/ye_first_vocals.wav', media / 'Kanye-verse.wav')

guitar = load(demucs / 'juice_first/other.wav')
# Use the guitar's own notes for the short transition into the last hook.
pick = guitar[round(24.192*SR):round(25.692*SR)][::-1]
pick = filt(filt(pick, 'highpass', 170), 'lowpass', 2400)
save('Guitar-pickup.wav', pick * np.linspace(0,1,len(pick),dtype=np.float32)[:,None]**1.5)
