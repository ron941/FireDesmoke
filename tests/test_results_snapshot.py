"""The rendered table source must preserve every author-supplied CSV cell."""
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_results_snapshot', ROOT/'scripts/build_results_snapshot.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

def test_author_csv_snapshot_is_current():
    snapshot = json.loads((ROOT/'site/dist/results.json').read_text())
    assert snapshot == builder.build()
    for dataset, (filename, _, name_column) in builder.TABLES.items():
        source = list(csv.DictReader((ROOT/'results'/filename).open(encoding='utf-8-sig')))
        rows = snapshot['datasets'][dataset]
        assert len(rows) == len(source)
        metrics = snapshot['source']['tables'][dataset]['metrics']
        for original, displayed in zip(source, rows):
            assert displayed['method'] == original[name_column]
            assert displayed['values'] == [original[column] for column in metrics]
    smoke = next(r for r in snapshot['datasets']['smokebench'] if r['method']=='FireDesmoke*')
    assert smoke['values'] == ['30.47', '0.890', '0.137']
    haze = next(r for r in snapshot['datasets']['haze'] if r['method']=='FireDesmoke')
    assert haze['values'] == ['25.65','22.35','19.49','15.96','30.92','22.87']
