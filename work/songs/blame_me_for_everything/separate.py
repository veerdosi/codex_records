"""Separate a source excerpt with the installed BS-RoFormer checkpoint."""
from pathlib import Path
import logging
import sys

import torch
from audio_separator.separator import Separator

song = Path(__file__).resolve().parent
torch.set_num_threads(4)
separator = Separator(
    log_level=logging.INFO,
    model_file_dir=str(song.parents[1]/'shared/models/roformer'),
    output_dir=str(song/'stems'), output_format='WAV',
    normalization_threshold=1, amplification_threshold=0,
    use_soundfile=True, use_native_fp16=True,
    mdxc_params={'segment_size':256,'override_model_segment_size':False,
                 'batch_size':1,'overlap':2,'pitch_shift':0},
)
separator.load_model(model_filename='model_bs_roformer_ep_317_sdr_12.9755.ckpt')
for excerpt in sys.argv[1:]:
    input_file = Path(excerpt)
    name = input_file.stem
    print(separator.separate(str(input_file),{
        'Vocals': name+'_vocals', 'Instrumental': name+'_instrumental'
    }),flush=True)
