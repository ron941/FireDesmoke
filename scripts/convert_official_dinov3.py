"""Convert the verified official HF ViT-L/16 checkpoint to Meta's state_dict format.

Reference: huggingface/transformers convert_dinov3_vit_to_hf.py.
No learned tensor is resampled or cast. K bias is masked out in Meta's model;
its zero values, fixed mask, and analytical RoPE periods are reconstructed.
"""
import argparse
import hashlib
import re
from pathlib import Path
import torch
from safetensors.torch import load_file

SOURCE_SHA256 = 'dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179'

def convert(source, output):
    source, output = Path(source), Path(output)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Expected the verified official LVD-1689M ViT-L/16 safetensors checkpoint.')
    if output.exists():
        raise FileExistsError(output)
    src = load_file(str(source))
    state={}
    consumed=set()
    for k,v in src.items():
     if re.match(r'layer.\d+.attention.[qkv]_proj.',k):continue
     key=k.replace('embeddings.cls_token','cls_token').replace('embeddings.mask_token','mask_token').replace('embeddings.register_tokens','storage_tokens').replace('embeddings.patch_embeddings','patch_embed.proj')
     key=re.sub(r'layer.(\d+).attention.o_proj',r'blocks.\1.attn.proj',key)
     key=re.sub(r'layer.(\d+).layer_scale(\d+).lambda1',r'blocks.\1.ls\2.gamma',key)
     key=re.sub(r'layer.(\d+).mlp.up_proj',r'blocks.\1.mlp.fc1',key)
     key=re.sub(r'layer.(\d+).mlp.down_proj',r'blocks.\1.mlp.fc2',key)
     key=re.sub(r'layer.(\d+).norm',r'blocks.\1.norm',key)
     state[key]=v.squeeze(1) if key=='mask_token' else v
     consumed.add(k)
    for i in range(24):
     pre=f'layer.{i}.attention.';dst=f'blocks.{i}.attn.qkv.'
     keys=[pre+c+'_proj.weight' for c in 'qkv']
     state[dst+'weight']=torch.cat([src[k] for k in keys]);consumed.update(keys)
     keys=[pre+c+'_proj.bias' for c in 'qv']
     state[dst+'bias']=torch.cat([src[keys[0]],torch.zeros_like(src[keys[0]]),src[keys[1]]]);consumed.update(keys)
     state[dst+'bias_mask']=torch.cat([torch.ones(1024),torch.zeros(1024),torch.ones(1024)])
     # Every split matrix/vector must survive the inverse conversion exactly.
     for c,t in zip('qkv',state[dst+'weight'].chunk(3)):assert torch.equal(t,src[pre+c+'_proj.weight'])
     for c,t in zip('qkv',state[dst+'bias'].chunk(3)):
      if c!='k':assert torch.equal(t,src[pre+c+'_proj.bias'])
    assert consumed==set(src),(set(src)-consumed)
    state['rope_embed.periods']=100**(2*torch.arange(16,dtype=torch.float32)/32)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, output)
    print(hashlib.sha256(output.read_bytes()).hexdigest(), output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    convert(args.input, args.output)
