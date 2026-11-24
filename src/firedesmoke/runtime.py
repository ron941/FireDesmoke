"""Author-supplied FireDesmoke model and paper inference, shared by CLI and demo."""
from pathlib import Path
import numpy as np
import torch
from .assets import read_json, verify_file, sha256
from .model import build
from .infer import restore

class RestorationEngine:
    def __init__(self,model_id,registry_path,assets_path,device='cuda'):
        registry=read_json(registry_path); assets=read_json(assets_path)
        entry=registry['models'][model_id]
        checkpoint=Path(assets['models'][model_id]);verify_file(checkpoint,entry['sha256'])
        deps=assets['dependencies']
        dino_hash=sha256(deps['dinov3_weights'])
        spec=registry['dependencies']['dinov3_weights']
        verified_hashes={item['sha256'] for item in spec.get('verified_alternatives', [])}
        if not (dino_hash.startswith(spec['sha256_prefix']) or dino_hash in verified_hashes):
            raise ValueError('DINOv3 checkpoint does not match the author-specified ViT-L/16 LVD-1689M hash.')
        if spec.get('sha256'):verify_file(deps['dinov3_weights'],spec['sha256'])
        adair=Path(deps['adair_repo'])/'net/model.py'
        adair_hash=registry['dependencies']['adair_repo'].get('model_sha256')
        if adair_hash:verify_file(adair,adair_hash)
        self.device=torch.device(device)
        if self.device.type=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA GPU is unavailable.')
        self.model=build(str(checkpoint),deps['adair_repo'],deps['dinov3_repo'],deps['dinov3_weights'],str(self.device))
        self.window=entry['inference']['window'];self.model_id=model_id
        self.provenance={'model_id':model_id,'checkpoint_sha256':entry['sha256'],
            'dinov3_sha256':dino_hash,'adair_model_sha256':sha256(adair),
            'window':self.window,'stride':self.window//4,'flip':True,'whole':False,'precision':'fp32',
            'tf32_matmul':torch.backends.cuda.matmul.allow_tf32,'tf32_cudnn':torch.backends.cudnn.allow_tf32,
            'model_sha256':sha256(Path(__file__).with_name('model.py')),
            'inference_sha256':sha256(Path(__file__).with_name('infer.py')),'torch':torch.__version__}

    @torch.inference_mode()
    def predict_array(self,rgb,*,pad=False,return_float=False):
        if rgb.dtype!=np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3:raise ValueError('Input must be RGB uint8 H×W×3.')
        if min(rgb.shape[:2])<16:raise ValueError('Both image sides must be at least 16 pixels.')
        x=torch.from_numpy(np.ascontiguousarray(rgb)).to(self.device).permute(2,0,1)[None].float()/255
        # restore() performs the author's padding, overlapping ramps and flip average.
        y=restore(self.model,x,window=self.window,flip=True,whole=False)
        if not torch.isfinite(y).all():raise RuntimeError('Model returned non-finite values.')
        result=(y*255+0.5).byte()[0].permute(1,2,0).cpu().numpy()
        if return_float:return result,y[0].permute(1,2,0).cpu().numpy()
        return result
