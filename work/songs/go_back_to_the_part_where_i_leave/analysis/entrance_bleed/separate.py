from pathlib import Path
import logging
import sys

import soundfile as sf
import torch
from audio_separator.separator import Separator

stage=Path(__file__).resolve().parent
root=stage.parents[4]
song=root/'work/songs/blame_me_for_everything'
with sf.SoundFile(song/'sources/runaway.wav') as f:
    f.seek(round(98*f.samplerate))
    x=f.read(round(16*f.samplerate),dtype='float32')
    sr=f.samplerate
source=stage/'Runaway source context.wav'
sf.write(source,x,sr,'FLOAT')
torch.set_num_threads(4)
sep=Separator(
    log_level=logging.INFO,model_file_dir=str(root/'work/shared/models/roformer'),
    output_dir=str(stage),output_format='WAV',normalization_threshold=1,
    amplification_threshold=0,use_soundfile=True,use_native_fp16=True,
    mdxc_params={'segment_size':1024,'override_model_segment_size':True,
        'batch_size':1,'overlap':4,'pitch_shift':0},
)
sep.load_model(model_filename='model_bs_roformer_ep_317_sdr_12.9755.ckpt')
sep.separate(str(source),{'Vocals':'Runaway all voices','Instrumental':'Runaway clean instrumental'})
