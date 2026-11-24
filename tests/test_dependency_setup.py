import importlib.util
import json
from pathlib import Path
import pytest
from firedesmoke.assets import sha256
from firedesmoke.cli import parser

spec = importlib.util.spec_from_file_location('fetch_dependencies', Path(__file__).resolve().parents[1]/'scripts/fetch_dependencies.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def test_authorized_encoder_identity(tmp_path):
    original = tmp_path/'original.pth'
    alternative = tmp_path/'alternative.pth'
    unknown = tmp_path/'unknown.pth'
    for path in (original, alternative, unknown):
        path.write_bytes(path.name.encode())
    rules = {'sha256_prefix': sha256(original)[:8], 'verified_alternatives': [{'sha256': sha256(alternative)}]}
    assert setup.checked_encoder(original, rules) == original
    assert setup.checked_encoder(alternative, rules) == alternative
    with pytest.raises(ValueError, match='verified'):
        setup.checked_encoder(unknown, rules)


@pytest.mark.parametrize('revision,dirty', [('wrong', ''), ('expected', ' M net/model.py')])
def test_changed_dependency_rejected(tmp_path, monkeypatch, revision, dirty):
    def output(command, **kwargs):
        return revision if 'rev-parse' in command else dirty
    monkeypatch.setattr(setup.subprocess, 'check_output', output)
    with pytest.raises(ValueError, match='clean source'):
        setup.checked_repo(tmp_path, {'commit':'expected'})


@pytest.mark.parametrize('command', ['train', 'evaluate'])
def test_undelivered_commands_not_exposed(command):
    with pytest.raises(SystemExit):
        parser().parse_args([command])


def test_paper_inference_model_defaults():
    registry = json.loads((Path(__file__).resolve().parents[1]/'registry/models.json').read_text())
    assert set(registry['models']) == {'firedesmoke', 'firedesmoke-smokebench'}
    for name, window in [('firedesmoke',384), ('firedesmoke-smokebench',320)]:
        cfg = registry['models'][name]['inference']
        assert cfg['window'] == window and cfg['stride'] == window//4
        assert cfg['flip'] is True and cfg['whole'] is False and cfg['precision'] == 'fp32'
