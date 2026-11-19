import glob
import os
import json
import librosa
import numpy as np
import torch
import argparse
from muq import MuQ
from hydra.utils import instantiate
from omegaconf import OmegaConf
from safetensors.torch import load_file
from tqdm import tqdm



class Synthesizer(object):

    def __init__(self,
                 checkpoint_path_reward_model,
                 input_path,
                 output_dir,
                 use_cpu: bool = False):

        self.checkpoint_path_reward_model = checkpoint_path_reward_model
        self.input_path = input_path
        if self.input_path[-1] == '/':
            self.input_path = self.input_path[:-1]
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.device = torch.device('cuda') if (torch.cuda.is_available() and (not use_cpu)) else torch.device('cpu')

    @torch.no_grad()
    def setup(self):

        train_config_reward_model = OmegaConf.load('configs/songbench.yaml')
        reward_model = instantiate(train_config_reward_model.generator).to(self.device).eval()
        state_dict_reward_model = load_file(self.checkpoint_path_reward_model, device="cpu")
        reward_model.load_state_dict(state_dict_reward_model, strict=False)
        self.reward_model = reward_model

        self.muq = MuQ.from_pretrained("OpenMuQ/MuQ-large-msd-iter")
        self.muq = self.muq.to(self.device).eval()
        self.result_dict = {}

    @torch.no_grad()
    def synthesis(self, model_name=None):
        if os.path.isfile(self.input_path):
            if self.input_path.endswith(('.wav', '.mp3','.flac')):
                lines = []
                lines.append(self.input_path)
            else:
                with open(self.input_path, "r") as f:
                    lines = [line for line in f]
            input_files = [{
                "input_path": line.strip(),
            } for line in lines]
            print(f"input filelst: {self.input_path}")
        elif os.path.isdir(self.input_path):
            input_files = [{
                "input_path": file,
            }for file in glob.glob(os.path.join(self.input_path, '*')) if file.lower().endswith(('.wav', '.mp3','.flac'))]
        else:
            raise ValueError(f"input_path {self.input_path} is not a file or directory")


        for input in tqdm(input_files):
            self.handle(**input)

        with open(os.path.join(self.output_dir, "result_average.json") , "a")as f:
            f.write(json.dumps({
                'path': self.input_path,
                'mean_Melody': round(np.mean([v['Melody'] for v in self.result_dict.values()]), 4),
                'mean_Arrangement': round(np.mean([v['Arrangement'] for v in self.result_dict.values()]), 4),
                'mean_Musicality': round(np.mean([v['Musicality'] for v in self.result_dict.values()]), 4),
                'mean_Vocal': round(np.mean([v['Vocal'] for v in self.result_dict.values()]), 4),
                'mean_Instrumental': round(np.mean([v['Instrumental'] for v in self.result_dict.values()]), 4),
                'mean_Mixing': round(np.mean([v['Mixing'] for v in self.result_dict.values()]), 4),
                'mean_Structure': round(np.mean([v['Structure'] for v in self.result_dict.values()]), 4),
            }, ensure_ascii=False) + '\n')

        if model_name is None:
            if 'suno1229' in self.input_path:
                model_name = self.input_path.split('/')[-2].split('_')
                model_name = '_'.join(model_name[5:])
            elif '/audios' in self.input_path:
                model_name = self.input_path.split('/')[-2]
            else:
                model_name = self.input_path.split('/')[-1]

        self.result_dict = dict(sorted(self.result_dict.items(), key=lambda item: item[0]))

        with open(os.path.join(self.output_dir, f"result_{model_name}.json") , "w")as f:
            json.dump(self.result_dict, f, indent=4, ensure_ascii=False)

        print(f"result saved to {os.path.join(self.output_dir, f'result_{model_name}.json')}")

    @torch.no_grad()
    def handle(self, input_path):
        try:
            print(input_path)
            fid = os.path.basename(input_path).split('.')[0]
            if input_path.endswith('.npy'):
                input = np.load(input_path)

                # check ssl
                if len(input.shape) == 3 and input.shape[0] != 1:
                    print('ssl_shape error', input_path)
                    return
                if np.isnan(input).any():
                    print('ssl nan', input_path)
                    return

                input = torch.from_numpy(input).to(self.device)
                if len(input.shape) == 2:
                    input = input.unsqueeze(0)

            if input_path.endswith(('.wav', '.mp3','.flac')):
                wav, sr = librosa.load(input_path, sr=24000)
                audio = torch.tensor(wav).unsqueeze(0).to(self.device)
                output = self.muq(audio, output_hidden_states=True)
                input = output["hidden_states"][6]

            values = {}
            scores_g = self.reward_model(input).squeeze(0)
            values['Melody'] = round(scores_g[0].item(), 4)
            values['Arrangement'] = round(scores_g[1].item(), 4)
            values['Musicality'] = round(scores_g[2].item(), 4)
            values['Vocal'] = round(scores_g[3].item(), 4)
            values['Instrumental'] = round(scores_g[4].item(), 4)
            values['Mixing'] = round(scores_g[5].item(), 4)
            values['Structure'] = round(scores_g[6].item(), 4)

            self.result_dict[fid] = values
        except Exception as e:
            print(f'Error processing {input_path}: {str(e)}')



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_path",
        type=str,
        required=True,
        help="Input audio: path to a single file, a text file listing audio paths, or a directory of audio files."
    )
    parser.add_argument(
        "-o", "--output_dir",
        type=str,
        required=True,
        help="Output directory for generated results (will be created if it doesn't exist)."
    )
    parser.add_argument(
        "--use_cpu",
        type=str,
        help="Force CPU mode even if a GPU is available.",
        default=False
    )

    args = parser.parse_args()

    reward_model_ckpt_path = "ckpt/songbench.safetensors"

    synthesizer = Synthesizer(checkpoint_path_reward_model=reward_model_ckpt_path,
                              input_path=args.input_path,
                              output_dir=args.output_dir,
                              use_cpu=args.use_cpu)

    synthesizer.setup()

    synthesizer.synthesis()
