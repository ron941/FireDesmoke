"""Build website tables losslessly from the author's 2026-11-16 CSV delivery."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    'fire': ('fire_test_1500_frames_all_methods.csv', 'S2', 'Method'),
    'smokebench': ('smokebench_official_eval.csv', 'S7', 'Method'),
    'realx3d': ('realx3d_rgb.csv', 'S8', 'Method'),
    'haze': ('public_dehazing_rgb_psnr.csv', 'S9', 'Model'),
}

def build():
    result = {'source': {'delivery': '2026-11-16', 'status': 'Author-reported manuscript results; not a local re-evaluation.', 'tables': {}}, 'datasets': {}}
    for dataset, (filename, table, name_column) in TABLES.items():
        path = ROOT / 'results' / filename
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            metrics = [key for key in reader.fieldnames if key not in ('Block', name_column)]
            rows = []
            for row in reader:
                name = row[name_column]
                group = row['Block'] or ('Reference input' if name == 'Input' else 'FireDesmoke')
                rows.append({'method': name, 'values': [row[key] for key in metrics], 'group': group})
        result['source']['tables'][dataset] = {'table': table, 'csv': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'metrics': metrics}
        result['datasets'][dataset] = rows
    return result

if __name__ == '__main__':
    (ROOT / 'site/dist/results.json').write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n')
