"""Separate the chosen excerpts with the installed lead-vocal checkpoint."""
from pathlib import Path
import logging
import sys

from audio_separator.separator import Separator
import soundfile as sf
import torch

here = Path(__file__).resolve().parent
song = here.parents[1]
torch.set_num_threads(4)
separator = Separator(
    log_level=logging.INFO,
    model_file_dir=str(song.parents[1]/'shared/models/roformer'),
    output_dir=str(here), output_format='WAV',
    normalization_threshold=1, amplification_threshold=0,
    use_soundfile=True, use_native_fp16=True,
    mdxc_params={'segment_size':1024, 'override_model_segment_size':True,
                 'batch_size':1, 'overlap':2, 'pitch_shift':0},
)
separator.load_model(model_filename='bs_roformer_karaoke_frazer_becruily.ckpt')
for name, start, end in zip(*[iter(sys.argv[1:])]*3):
    with sf.SoundFile(song/'sources'/f'{name}.wav') as source:
        sr=source.samplerate
        source.seek(round(float(start)*sr))
        clip=source.read(round((float(end)-float(start))*sr),dtype='float32')
    source_path=here/f'{name} excerpt.wav'
    sf.write(source_path,clip,sr,'FLOAT')
    separator.separate(str(source_path),{'Vocals':f'{name} lead', 'Instrumental':f'{name} backing'})
