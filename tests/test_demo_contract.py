"""CPU-only demo contract tests. Stub outputs do not validate model quality/parity."""
import hashlib
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from firedesmoke import demo


class StubEngine:
    provenance = {'model_id': 'cpu-contract-stub', 'checkpoint_sha256': 'test-only'}

    def __init__(self):
        self.calls = []
        self.error = None

    def predict_array(self, array, *, pad):
        self.calls.append((array.copy(), pad))
        if self.error:
            raise self.error
        return np.full_like(array, 73)


@pytest.fixture
def demo_callbacks(tmp_path):
    pytest.importorskip('gradio')
    engine = StubEngine()
    app = demo.build_app(engine, tmp_path)
    callbacks = {f.api_name: f for f in app.fns.values()}
    return engine, app, callbacks, tmp_path


def make_image(path, size=(641, 477)):
    Image.new('RGB', size, (13, 31, 59)).save(path)
    return str(path)


def test_uploaded_image_clears_old_result_and_explains_size(demo_callbacks):
    _, app, callbacks, root = demo_callbacks
    original = make_image(root / 'source.png')
    prepared, info, comparison, download, status = callbacks['preview'].fn(original)
    assert prepared.size == (640, 476)
    assert '641 × 477' in info and '640 × 476' in info
    assert comparison is None and download is None
    assert 'Ready' in status
    # A new upload must update the old result widgets as well as the input preview.
    upload_outputs = {component._id for component in callbacks['preview'].outputs}
    restore_outputs = {component._id for component in callbacks['restore'].outputs[:3]}
    assert restore_outputs <= upload_outputs


def test_invalid_upload_clears_prior_result(demo_callbacks):
    _, _, callbacks, root = demo_callbacks
    path = root / 'broken.png'; path.write_bytes(b'not an image')
    prepared, info, comparison, download, status = callbacks['preview'].fn(str(path))
    assert prepared is None and comparison is None and download is None
    assert 'valid PNG or JPEG' in info
    assert 'supported image' in status


def test_restore_geometry_download_and_isolated_requests(demo_callbacks):
    engine, _, callbacks, root = demo_callbacks
    path = make_image(root / 'odd.png', (639, 477))
    first = callbacks['restore'].fn(path)
    second = callbacks['restore'].fn(path)
    assert first[1] != second[1]
    for result in (first, second):
        pair, filename, status = result[:3]
        assert pair[0].size == pair[1].size == (639, 477)
        assert status.startswith('Done.')
        with Image.open(filename) as output:
            assert output.format == 'PNG' and output.mode == 'RGB'
            assert output.size == (639, 477)
            assert np.asarray(output).min() == np.asarray(output).max() == 73
        record = json.loads(Path(filename).with_name('_run.json').read_text())
        assert record['padding_right'] == 1 and record['padding_bottom'] == 3
        assert record['output_sha256'] == hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    assert all(pad is True and image.shape == (477, 639, 3) for image, pad in engine.calls)


def test_backend_failure_clears_success_and_recovers(demo_callbacks):
    engine, _, callbacks, root = demo_callbacks
    path = make_image(root / 'source.png', (32, 32))
    engine.error = RuntimeError('Contract-only simulated failure')
    comparison, download, status = callbacks['restore'].fn(path)[:3]
    assert comparison is None and download is None and 'failed' in status
    engine.error = None
    assert callbacks['restore'].fn(path)[2].startswith('Done.')


def test_queue_and_external_font_contract(demo_callbacks):
    _, app, callbacks, _ = demo_callbacks
    assert app._queue.max_size == 8
    assert callbacks['restore'].concurrency_limit == 1
    assert callbacks['restore'].concurrency_id == 'firedesmoke-model'
    assert app.analytics_enabled is False
    assert app.delete_cache == (60, 3600)
    assert not app.theme._font_css


def test_launch_cleanup_and_loopback_options(tmp_path, monkeypatch):
    from firedesmoke import runtime
    cache = tmp_path / 'gradio-cache'
    stale = cache / 'stale'; stale.mkdir(parents=True)
    current = cache / 'current'; current.mkdir()
    (stale / 'old.png').write_bytes(b'old-private-upload')
    (current / 'recent.png').write_bytes(b'recent-private-upload')
    old = time.time() - 7200
    for p in (stale / 'old.png', stale):
        os.utime(p, (old, old))
    called = {}
    class FakeApp:
        def launch(self, **kwargs):called.update(kwargs)
    monkeypatch.setattr(runtime, 'RestorationEngine', lambda *args: StubEngine())
    monkeypatch.setattr(demo, 'build_app', lambda *args: FakeApp())
    monkeypatch.setenv('GRADIO_TEMP_DIR', '')
    monkeypatch.setenv('GRADIO_ANALYTICS_ENABLED', 'False')
    args = SimpleNamespace(workdir=str(tmp_path), model='firedesmoke', registry='unused', assets='unused', device='cpu', port=7860)
    demo.launch(args)
    assert not stale.exists() and current.exists()
    assert called['server_name'] == '127.0.0.1'
    assert called['share'] is False and called['show_error'] is False
    assert called['max_file_size'] == '20mb'
    assert called['allowed_paths'] == [str(tmp_path / 'requests')]


def test_cache_sweep_expires_previous_process_files(tmp_path):
    cache = tmp_path / 'gradio-cache'; old_dir = cache / 'previous'; old_dir.mkdir(parents=True)
    protected_dir = cache / 'active'; protected_dir.mkdir()
    old_file = old_dir / 'input.png'; old_file.write_bytes(b'previous-process-upload')
    active_file = protected_dir / 'input.png'; active_file.write_bytes(b'active-input')
    ancient = time.time() - 7200
    for path in (old_file, old_dir, active_file, protected_dir):os.utime(path, (ancient, ancient))
    demo.clean_expired_cache(cache, protected=[active_file])
    assert not old_dir.exists() and active_file.exists()
    demo.clean_expired_cache(cache)
    assert not protected_dir.exists()


def test_no_input_releases_controls(demo_callbacks):
    _, _, callbacks, _ = demo_callbacks
    comparison, download, status, upload, run = callbacks['restore'].fn(None)
    assert comparison is None and download is None and 'choose' in status
    assert upload['interactive'] is True and run['interactive'] is True


def test_initial_examples_survive_cache_expiry(tmp_path, monkeypatch):
    pytest.importorskip('gradio')
    cache = tmp_path / 'gradio-cache'
    monkeypatch.setenv('GRADIO_TEMP_DIR', str(cache))
    source = make_image(tmp_path / 'example.png')
    (tmp_path / 'examples.json').write_text(json.dumps([{'path': source, 'label': 'Example'}]))
    app = demo.build_app(StubEngine(), tmp_path)
    gallery = next(c for c in app.blocks.values() if c.elem_id == 'examples')
    thumbnail = Path(gallery.value[0]['image']['path'])
    assert thumbnail.is_relative_to(cache) and thumbnail.is_file()
    stale = cache / 'expired-upload' / 'upload.png'
    stale.parent.mkdir(); stale.write_bytes(b'expired upload')
    active = cache / 'active-upload' / 'upload.png'
    active.parent.mkdir(); active.write_bytes(b'in-flight upload')
    ancient = time.time() - 7200
    for path in sorted(cache.rglob('*'), reverse=True):
        os.utime(path, (ancient, ancient))
    demo.clean_demo_cache(cache, app, active_uploads=[active])
    assert thumbnail.is_file(), 'The initial gallery URL must remain valid after expiry'
    assert not stale.exists() and active.exists()
    demo.clean_demo_cache(cache, app)
    assert thumbnail.is_file() and not active.exists()
