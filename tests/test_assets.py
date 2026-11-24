import json
import pytest
from firedesmoke.assets import acquire,sha256

def test_verified_import_and_failed_hash(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'known weight')
    registry=tmp_path/'registry.json';registry.write_text(json.dumps({'models':{'m':{'filename':'m.pt','sha256':sha256(source)}}}))
    got=acquire('m',registry,tmp_path/'dest',source)
    assert got.read_bytes()==source.read_bytes()
    got.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='SHA256'):acquire('m',registry,tmp_path/'dest',source)

def test_no_fake_download(tmp_path):
    registry=tmp_path/'r.json';registry.write_text(json.dumps({'models':{'m':{'filename':'m.pt','sha256':'0'*64}}}))
    with pytest.raises(ValueError,match='No authorized'):acquire('m',registry,tmp_path/'dest')
