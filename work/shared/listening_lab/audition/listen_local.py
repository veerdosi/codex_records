import argparse
from pathlib import Path
import json
import os
import subprocess
import sys

home=Path(__file__).resolve().parent
source=home/'TinyMU'
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
sys.path.insert(0,str(home/'deps'))
sys.path.insert(0,str(source/'src'))

import numpy as np
import torch
import yaml
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
from safetensors.torch import load_file
from models.m2t import m2t
from models.matpac import model as matpac

def load_model():
    torch.set_num_threads(3)
    config=yaml.safe_load((source/'ckpt/tinymu.yaml').read_text())['model']
    # The released checkpoint contains all encoder and decoder tensors. Build their architectures first.
    matpac.get_matpac=lambda **kw: matpac.matpac_wrapper(inference_type='precise',
                               pull_time_dimension=kw['pull_time_dimension'],cfg=matpac.general_config())
    lm_config=AutoConfig.from_pretrained(home/'smol')
    orig=AutoModelForCausalLM.from_pretrained
    try:
        AutoModelForCausalLM.from_pretrained=lambda *a,**kw: AutoModelForCausalLM.from_config(lm_config)
        model=m2t(config)
    finally:
        AutoModelForCausalLM.from_pretrained=orig
    checkpoint=source/'ckpt/tinymu.safetensors'
    model.load_state_dict(load_file(str(checkpoint)),strict=True)
    tokenizer=AutoTokenizer.from_pretrained(home/'smol')
    tokenizer.add_special_tokens({'pad_token':'!'})
    return model.eval(),tokenizer

def decode(path,start,duration):
    out=subprocess.check_output(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t',str(duration),
                   '-ac','1','-ar','16000','-f','f32le','pipe:1'])
    return np.frombuffer(out,dtype='<f4').copy()

class Listener:
    def __init__(self,model,tokenizer):
        self.model=model
        self.tokenizer=tokenizer
        self.lm=model.text_decoder.lm

    def audio_tokens(self,audio):
        x=torch.from_numpy(audio).unsqueeze(0)
        encoded=self.model.audio_encoder(x,[x.shape[-1]])
        projected=self.model.projector(encoded)
        sep=self.model.text_decoder.embed_fn(torch.tensor([[self.model.text_decoder.sep_token_id]]))
        return torch.cat([projected,sep],dim=1)

    def prefix(self,embeds,prompt):
        tokens=self.tokenizer(prompt,return_tensors='pt',add_special_tokens=True,
                              truncation=True,padding='max_length',
                              max_length=self.model.max_text_token_len)
        prefix=torch.cat([embeds,self.model.text_decoder.embed_fn(tokens.input_ids)],dim=1)
        mask=torch.cat([torch.ones(embeds.shape[:2],dtype=torch.long),tokens.attention_mask],dim=1)
        return prefix,mask

    def answer(self,embeds,prompt,max_new_tokens=48):
        prefix,mask=self.prefix(embeds,prompt)
        positions=torch.arange(prefix.shape[1]).unsqueeze(0)
        tokens=[]
        cache=None
        for _ in range(max_new_tokens):
            out=self.lm(inputs_embeds=prefix,attention_mask=mask,position_ids=positions,
                        past_key_values=cache,use_cache=True)
            token=out.logits[:,-1].argmax(-1,keepdim=True)
            if token.item() in (self.tokenizer.eos_token_id,self.tokenizer.convert_tokens_to_ids('<|endoftext|>')):
                break
            tokens.append(token.item())
            cache=out.past_key_values
            prefix=self.model.text_decoder.embed_fn(token)
            mask=torch.cat([mask,torch.ones_like(token)],dim=1)
            positions=positions[:,-1:]+1
        return self.tokenizer.decode(tokens,skip_special_tokens=True).strip()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('audio',type=Path)
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--end',type=float)
    parser.add_argument('--prompt',default='Caption the music')
    args=parser.parse_args()
    model,tokenizer=load_model()
    listener=Listener(model,tokenizer)
    print('TinyMU ready',flush=True,file=sys.stderr)
    with torch.inference_mode():
        end=args.end
        if end is None:
            end=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
                                          '-of','csv=p=0',str(args.audio)]))
        start=args.start
        while start<end-.3:
            stop=min(end,start+10)
            wav=decode(args.audio,start,stop-start)
            if len(wav)<16000//3: break
            audio=listener.audio_tokens(wav)
            response=listener.answer(audio,args.prompt,max_new_tokens=80)
            print(json.dumps({'start':start,'end':stop,'caption':response}),flush=True)
            start=stop

if __name__=='__main__':
    main()
