from pathlib import Path
import argparse
import gc
import json
import sys
import time

import numpy as np
import soundfile as sf
import torch
import yaml

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base/'upstream'))
from models.scnet import SCNet
from demucs.apply import apply_model
from demucs.pretrained import get_model

root = base.parents[3]
sys.path.insert(0, str(root/'work'))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from dsp import filt, SR

parser = argparse.ArgumentParser(description='Repeat the archived two-excerpt separation comparison.')
parser.add_argument('fixture_dir', type=Path, help='Folder containing stems/{flash,juice}/{original,other}.wav')
tracks = parser.parse_args().fixture_dir
for name in ('flash', 'juice'):
    for source in ('original', 'other'):
        fixture = tracks / 'stems' / name / f'{source}.wav'
        if not fixture.is_file():
            parser.error(f'Missing fixture {fixture}')
cases = {'flash':(106.0, 180), 'juice':(23.13, 220)}
duration = 8
margin = 1.5

def read(path, start, duration):
    x, sr = sf.read(path, start=round(start*SR), frames=round(duration*SR),
                    always_2d=True, dtype='float32')
    assert sr == SR and len(x) == round(duration*SR)
    return x

def metrics(x, name):
    y = filt(filt(x,'highpass',cases[name][1]),'lowpass',6400 if name=='flash' else 5600)
    rms = float(np.sqrt(np.mean(y*y)))
    aligned = y * (10**(-24/20)/rms)
    side = (aligned[:,0]-aligned[:,1])/2
    mid = aligned.mean(axis=1)
    return {
        'matched_side_peak_dbfs':round(20*np.log10(max(1e-10,np.max(abs(side)))),2),
        'matched_mid_peak_dbfs':round(20*np.log10(max(1e-10,np.max(abs(mid)))),2),
        'side_impulse_count':int(np.sum(abs(side)>.5)),
        'stereo_correlation':round(float(np.corrcoef(aligned.T)[0,1]),3),
    }

torch.set_num_threads(4)
torch.manual_seed(87)
cfg = yaml.load((base/'config.yaml').read_text(), Loader=yaml.FullLoader)
assert cfg['audio']['chunk_size'] == round((duration+2*margin)*SR)
model = SCNet(**cfg['model'])
model.load_state_dict(torch.load(base/'scnet_xl.ckpt',map_location='cpu',mmap=True,weights_only=True), strict=True)
model.eval()
out={}
pieces={}
start_slice = slice(round(margin*SR),round((margin+duration)*SR))
for name, (start, _) in cases.items():
    # Use the preserved 44.1 kHz input from the original separation for both models.
    audio = read(tracks/f'stems/{name}/original.wav',start-margin,duration+2*margin)
    pieces[name]=audio
    mix=torch.from_numpy(audio.T.copy())
    before=time.monotonic()
    print('SCNet XL',name,'CPU',flush=True)
    with torch.inference_mode():
        stems=model(mix[None])[0]
    audio_out=stems[cfg['model']['sources'].index('other')].numpy().T[start_slice]
    assert audio_out.shape==(duration*SR,2) and np.isfinite(audio_out).all()
    old=read(tracks/f'stems/{name}/other.wav',start,duration)
    out[name]={'original_start':start,'duration':duration,'scnet_device':'cpu',
               'SCNet XL IHF':metrics(audio_out,name),
               'legacy Demucs vocal specialist other output':metrics(old,name)}
    print(name,out[name],round(time.monotonic()-before,1),flush=True)
    (base/'results.json').write_text(json.dumps(out,indent=2))
del model, stems
gc.collect()
torch.mps.empty_cache()

# The legacy mix came from one specialist in the bundle, so test the full bundle as a control.
bundle = get_model('htdemucs_ft').eval()
for name, audio in pieces.items():
    print('Full Demucs',name,flush=True)
    mix=torch.from_numpy(audio.T.copy())
    with torch.no_grad():
        stems=apply_model(bundle,mix[None],device='mps',shifts=1,split=True,overlap=.35,segment=7)[0]
    stem=stems[bundle.sources.index('other')].cpu().numpy().T[start_slice]
    assert stem.shape==(duration*SR,2) and np.isfinite(stem).all()
    out[name]['Full htdemucs_ft']=metrics(stem,name)
    (base/'results.json').write_text(json.dumps(out,indent=2))
    print(name,out[name]['Full htdemucs_ft'],flush=True)
print('Separation check complete',flush=True)
