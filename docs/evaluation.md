# Reported results and evaluation availability

The authors' 2026-11-16 delivery supplies four CSVs in [`results/`](../results/):

| File | Manuscript table | Model |
|---|---|---|
| `fire_test_1500_frames_all_methods.csv` | S2; selected rows in main Table 2 | FireDesmoke |
| `smokebench_official_eval.csv` | S7 | FireDesmoke* |
| `realx3d_rgb.csv` | S8 | FireDesmoke |
| `public_dehazing_rgb_psnr.csv` | S9 | FireDesmoke |

These are author-reported scores. Model-wrapper parity and example inference are
separate checks; they do not establish dataset-score reproduction. The current
training and scoring programs will be supplied separately. No updated chamber
CSV was included, so this delivery cannot establish a new chamber score.

SmokeBench uses its official Y-channel evaluation (4-pixel border crop and AlexNet
LPIPS). RealX3D and public-haze CSVs use RGB metrics. Preserve the original column
names and averaging conventions rather than comparing unlike metrics.

CSV annotations: `*` denotes SmokeBench-only training; `†` denotes outputs
released by the SmokeBench authors; `◇` denotes versions trained or adjusted with
other data; public-haze `#` denotes weights trained on that dataset.

To generate predictions, use native `firedesmoke infer` with the appropriate
checkpoint. The default is 384 windows / stride 96 / flip averaging; SmokeBench
uses 320 / 80 / flip averaging. No automatic input resize is applied by native
inference. The demo's long-edge-640 adapter is not a benchmark preprocessing rule.
Keep `_run.json` with the PNGs. See [README](../README.md) for commands.
