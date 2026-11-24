"""Verify saved restoration images against their inference manifest."""
import hashlib
import json
from pathlib import Path

from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1]
    site = root / 'site/dist'
    registry = json.loads((root / 'registry/models.json').read_text())
    images = json.loads((root / 'registry/website_inference.json').read_text())['images']
    assert len({item['output'] for item in images}) == len(images)
    for item in images:
        for role in ('input', 'output'):
            path = site / item[role]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item[role + '_sha256'], path
            with Image.open(path) as image:
                assert image.size == tuple(item['size']), path
        model = registry['models'][item['model']]
        actual = item['provenance']
        assert actual['checkpoint_sha256'] == model['sha256']
        for setting in ('window', 'stride', 'flip', 'whole', 'precision'):
            assert actual[setting] == model['inference'][setting], (item['output'], setting)
    for item in json.loads((site / 'homepage-cases.json').read_text())['cases']:
        for role in ('input', 'output'):
            assert hashlib.sha256((site / item[role]).read_bytes()).hexdigest() == item[role + '_sha256']
    print(f'PASS {len(images)} restoration images: hashes, sizes, checkpoints and paper settings')


if __name__ == '__main__':
    main()
