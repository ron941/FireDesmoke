"""Hash-checked local import and optional HTTPS model retrieval."""
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text())

def verify_file(path, expected):
    if not expected or len(expected)!=64:
        raise ValueError('A verified SHA256 is required for this asset.')
    if not Path(path).is_file(): raise FileNotFoundError(f'Model asset missing: {Path(path).name}')
    if sha256(path)!=expected: raise ValueError(f'SHA256 mismatch: {Path(path).name}')

def acquire(model_id, registry_path, destination, source=None):
    registry=read_json(registry_path)
    if model_id not in registry['models']: raise ValueError(f'Unknown model ID: {model_id}')
    entry=registry['models'][model_id]
    filename=entry['filename']
    if Path(filename).name!=filename: raise ValueError('Registry filename must be a basename.')
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    target=destination/filename
    if target.exists():
        verify_file(target,entry['sha256']); return target
    url=entry.get('download_url')
    if not source and not url:
        raise ValueError('No authorized download URL is configured. Use --source to import the supplied checkpoint.')
    fd,tmp=tempfile.mkstemp(prefix='.import-',dir=destination); os.close(fd)
    try:
        if source: shutil.copyfile(source,tmp)
        else:
            if not url.startswith('https://'): raise ValueError('Only HTTPS downloads are supported.')
            with urllib.request.urlopen(url,timeout=60) as response, open(tmp,'wb') as f:
                shutil.copyfileobj(response,f)
        verify_file(tmp,entry['sha256']); os.replace(tmp,target)
    finally:
        if Path(tmp).exists(): Path(tmp).unlink()
    return target
