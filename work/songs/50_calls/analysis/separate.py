from pathlib import Path
import logging,sys
import torch
from audio_separator.separator import Separator
p=Path(__file__).resolve().parent
torch.set_num_threads(3)
s=Separator(log_level=logging.INFO,model_file_dir=str(Path(__file__).resolve().parents[3] / 'shared/models/roformer'),output_dir=str(p.parent/'stems'),output_format='WAV',normalization_threshold=1,amplification_threshold=0,use_soundfile=True,use_native_fp16=True,mdxc_params={'segment_size':256,'override_model_segment_size':False,'batch_size':1,'overlap':2,'pitch_shift':0})
s.load_model(model_filename='model_bs_roformer_ep_317_sdr_12.9755.ckpt')
for name in sys.argv[1:]:
    s.separate(str(p/f'{name}.wav'),{'Vocals':name+'_vocals','Instrumental':name+'_instrumental'})
