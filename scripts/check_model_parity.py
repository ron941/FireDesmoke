"""Compare package inference with the author's standalone model/infer delivery."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import torch
from firedesmoke.assets import sha256
from firedesmoke.runtime import RestorationEngine


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', required=True, help='Author directory containing model.py and infer.py')
    p.add_argument('--model', choices=['firedesmoke', 'firedesmoke-smokebench'], required=True)
    p.add_argument('--assets', default='.local/asset_locations.json')
    p.add_argument('--registry', default='registry/models.json')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--device', default='cuda')
    a = p.parse_args()
    origin = Path(a.original).resolve()
    assets = json.loads(Path(a.assets).read_text())
    engine = RestorationEngine(a.model, a.registry, a.assets, a.device)
    bgr = cv2.imread(a.input, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError('Cannot decode input')
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    actual = engine.predict_array(rgb)
    provenance = engine.provenance
    window = engine.window
    del engine
    if str(a.device).startswith('cuda'):
        torch.cuda.empty_cache()
    # The unmodified author infer.py imports its neighboring model as "model".
    original_model = load(origin/'model.py', 'author_model_for_parity')
    previous = sys.modules.get('model')
    sys.modules['model'] = original_model
    try:
        original_infer = load(origin/'infer.py', 'author_infer_for_parity')
    finally:
        if previous is None:
            sys.modules.pop('model', None)
        else:
            sys.modules['model'] = previous
    d = assets['dependencies']
    model = original_model.build(assets['models'][a.model], d['adair_repo'], d['dinov3_repo'], d['dinov3_weights'], a.device)
    x = torch.from_numpy(np.ascontiguousarray(rgb)).to(a.device).permute(2,0,1)[None].float()/255
    with torch.inference_mode():
        y = original_infer.restore(model, x, window=window, flip=True, whole=False)
    expected = (y*255+0.5).byte()[0].permute(1,2,0).cpu().numpy()
    error = np.abs(expected.astype(np.int16)-actual.astype(np.int16))
    report = {'model': a.model, 'input_sha256': sha256(a.input), 'author_model_sha256': sha256(origin/'model.py'),
              'author_infer_sha256': sha256(origin/'infer.py'), 'max_8bit_error': int(error.max()),
              'png_equal': bool(np.array_equal(expected, actual)), 'environment': provenance,
              'scope': 'Same input, checkpoint, dependencies and environment; not full-dataset score reproduction.'}
    Path(a.output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if not report['png_equal']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
