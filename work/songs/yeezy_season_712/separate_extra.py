from pathlib import Path
import logging
import torch
from audio_separator.separator import Separator

home=Path(__file__).resolve().parent
torch.set_num_threads(3)
model_dir=Path(__file__).resolve().parents[2] / 'shared/models/roformer'
sep=Separator(log_level=logging.INFO,model_file_dir=str(model_dir),output_dir=str(home/'stems'),
              output_format='WAV',normalization_threshold=1,amplification_threshold=0,
              use_soundfile=True,use_native_fp16=True,
              mdxc_params={'segment_size':256,'override_model_segment_size':False,
                           'batch_size':1,'overlap':2,'pitch_shift':0})
sep.load_model(model_filename='model_bs_roformer_ep_317_sdr_12.9755.ckpt')
for path in [home/'input/facts_extra.wav']:
    print(path.stem,flush=True)
    names=sep.separate(str(path),{'Vocals':path.stem+'_vocals','Instrumental':path.stem+'_instrumental'})
    print(names,flush=True)
