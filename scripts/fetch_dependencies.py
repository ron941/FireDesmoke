"""Prepare pinned official source and authorized local weights; never store tokens."""
import argparse
import json
import subprocess
from pathlib import Path
from firedesmoke.assets import verify_file, sha256


def checked_repo(target, entry, architecture=False):
    target = Path(target).resolve()
    if not target.exists():
        subprocess.run(['git', 'clone', entry['url'], str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', entry['commit']], check=True)
    actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(target), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    if actual != entry['commit'] or dirty:
        raise ValueError(f'{target.name}: require clean source at {entry["commit"]}; use another destination.')
    if architecture:
        verify_file(target / 'net/model.py', entry['model_sha256'])
    return target


def checked_encoder(path, spec):
    path = Path(path).resolve()
    digest = sha256(path)
    accepted = {a['sha256'] for a in spec.get('verified_alternatives', [])}
    if not (digest.startswith(spec['sha256_prefix']) or digest in accepted):
        raise ValueError('DINOv3 weight is not the authorized, verified ViT-L/16 LVD-1689M checkpoint.')
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', default='registry/models.json')
    p.add_argument('--destination', default='.local/dependencies')
    p.add_argument('--weights', default='.local/weights')
    p.add_argument('--assets-output', default='.local/asset_locations.json')
    p.add_argument('--adair-repo')
    p.add_argument('--dinov3-repo')
    p.add_argument('--dinov3-weights', required=True, help='Authorized original or verified converted Meta-format weight')
    a = p.parse_args()
    registry = json.loads(Path(a.registry).read_text())
    dependencies = registry['dependencies']
    # Validate the large authorized weight before any network request.
    encoder = checked_encoder(a.dinov3_weights, dependencies['dinov3_weights'])
    dest = Path(a.destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    adair = checked_repo(a.adair_repo or dest/'adair', dependencies['adair_repo'], architecture=True)
    dino = checked_repo(a.dinov3_repo or dest/'dinov3', dependencies['dinov3_repo'])
    ap = Path(a.assets_output)
    assets = json.loads(ap.read_text()) if ap.exists() else {'models': {}}
    assets['dependencies'] = {'adair_repo': str(adair), 'dinov3_repo': str(dino), 'dinov3_weights': str(encoder)}
    for name, entry in registry['models'].items():
        checkpoint = Path(a.weights).resolve()/entry['filename']
        if checkpoint.is_file():
            verify_file(checkpoint, entry['sha256'])
            assets.setdefault('models', {})[name] = str(checkpoint)
    ap.parent.mkdir(parents=True, exist_ok=True)
    temp = ap.with_suffix('.tmp')
    temp.write_text(json.dumps(assets, indent=2)+'\n')
    temp.replace(ap)
    print(f'Verified dependencies and wrote {ap}. Registered {len(assets.get("models", {}))} local model(s).')


if __name__ == '__main__':
    main()
