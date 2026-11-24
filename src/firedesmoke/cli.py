import argparse
import json
import sys
from pathlib import Path

def parser():
    p=argparse.ArgumentParser(prog='firedesmoke',description='FireDesmoke inference and image restoration demo.')
    sub=p.add_subparsers(dest='command',required=True)
    dl=sub.add_parser('download'); dl.add_argument('--model',required=True); dl.add_argument('--registry',default='registry/models.json');dl.add_argument('--destination',default='.local/weights');dl.add_argument('--source')
    inf=sub.add_parser('infer'); inf.add_argument('--model',required=True);inf.add_argument('--registry',default='registry/models.json');inf.add_argument('--assets',default='.local/asset_locations.json');inf.add_argument('--device',default='cuda');inf.add_argument('--input',required=True);inf.add_argument('--output',required=True);inf.add_argument('--adapter',choices=['native','demo'],default='native')
    dm=sub.add_parser('demo');dm.add_argument('--model',default='firedesmoke');dm.add_argument('--registry',default='registry/models.json');dm.add_argument('--assets',default='.local/asset_locations.json');dm.add_argument('--device',default='cuda');dm.add_argument('--port',type=int,default=7860);dm.add_argument('--workdir',default='.local/demo')
    return p

def infer(a):
    from .runtime import RestorationEngine
    from .images import read_image,prepare_demo,as_rgb_array
    from .assets import sha256
    from PIL import Image
    import time,hashlib
    src=Path(a.input);dst=Path(a.output)
    paths=[src] if src.is_file() else sorted(p for p in src.rglob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg'} and p.is_file())
    if not paths: raise ValueError('No PNG/JPEG inputs found.')
    names=[(p.name if src.is_file() else str(p.relative_to(src))) for p in paths]
    outputs=[dst/Path(n).with_suffix('.png') for n in names]
    if len(set(outputs))!=len(outputs): raise ValueError('Input stems collide after PNG conversion.')
    if dst.exists() and any(dst.iterdir()): raise ValueError('Output directory must be empty to avoid mixing runs.')
    engine=RestorationEngine(a.model,a.registry,a.assets,a.device)
    dst.mkdir(parents=True,exist_ok=True)
    cfg={'model':a.model,'adapter':a.adapter,**engine.provenance}
    digest=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    record={'status':'running','configuration':cfg,'configuration_sha256':digest,'frames':[]}
    def persist():
        temp=dst/'_run.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(dst/'_run.json')
    persist()
    try:
        for inp,out,name in zip(paths,outputs,names):
            start=time.perf_counter();im=read_image(inp,demo=a.adapter=='demo')
            meta={'original_size':list(im.size),'inference_size':list(im.size)}
            if a.adapter=='demo': im,meta=prepare_demo(im)
            prediction=engine.predict_array(as_rgb_array(im),pad=a.adapter=='demo')
            out.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(prediction).save(out,format='PNG')
            record['frames'].append({'frame_id':name,'input_sha256':sha256(inp),'output':str(out.relative_to(dst)),'output_sha256':sha256(out),'seconds':time.perf_counter()-start,**meta})
            persist()
        record['status']='complete';persist()
    except Exception:
        record['status']='failed';persist();raise
    print(f'Completed {len(paths)} images. Manifest: {dst / "_run.json"}')

def main():
    a=parser().parse_args()
    try:
        if a.command=='download':
            from .assets import acquire
            print(acquire(a.model,a.registry,a.destination,a.source))
        elif a.command=='infer': infer(a)
        else:
            from .demo import launch
            launch(a)
    except (ValueError,RuntimeError,FileNotFoundError,KeyError) as e:
        print(f'Error: {e}',file=sys.stderr);return 1
    return 0

if __name__=='__main__': sys.exit(main())
