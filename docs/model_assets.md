# Model assets

The two 2026-11-16 author checkpoints are registered with full SHA256 checks in
[`registry/models.json`](../registry/models.json):

| Model ID | File | Use |
|---|---|---|
| `firedesmoke` | `firedesmoke_full.pt` | Full model; fire, RealX3D, public haze, chamber and default demo |
| `firedesmoke-smokebench` | `firedesmoke_smokebench.pt` | SmokeBench-only training; FireDesmoke* table |

Import each authorized checkpoint with `firedesmoke download --model MODEL --source FILE`.
The dependency setup helper checks the imported files in `.local/weights` and adds
those found to `.local/asset_locations.json`:

```bash
python scripts/fetch_dependencies.py --dinov3-weights /path/to/authorized/dinov3.pth
```

Use `--adair-repo /existing/AdaIR --dinov3-repo /existing/dinov3` to reuse
checkouts at the exact revisions recorded in the registry. Otherwise the helper
clones the official repositories under `.local/dependencies`. It verifies the
AdaIR architecture file and rejects dirty or mismatched repositories. No AdaIR
pretrained weight is needed. DINOv3 ViT-L/16 LVD-1689M must be obtained under its
official access terms; [the verified HF conversion](dinov3_weights.md) is also accepted.

A manual local map has this structure (absolute paths recommended):

```json
{
  "models": {
    "firedesmoke": "/path/to/firedesmoke_full.pt",
    "firedesmoke-smokebench": "/path/to/firedesmoke_smokebench.pt"
  },
  "dependencies": {
    "adair_repo": "/path/to/AdaIR",
    "dinov3_repo": "/path/to/dinov3",
    "dinov3_weights": "/path/to/authorized/dinov3.pth"
  }
}
```

Pass a different map with `--assets /path/to/assets.json`. The runtime verifies
checkpoint identities before loading. Neither weights nor authorization tokens
are included in Git or the installed package.
