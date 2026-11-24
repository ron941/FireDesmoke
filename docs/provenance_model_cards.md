# Model cards

Both checkpoints use AdaIR + frozen DINOv3 ViT-L/16 (LVD-1689M), Semantic
Rectification and local fusion at 1/4 and 1/8 resolution. They accept a single
RGB image; no clean reference, evaluation mask or smoke field is needed at inference.
The approximately 30.87M model parameters are supplied separately from DINOv3.

| ID | Checkpoint | Evaluation use | Window / stride |
|---|---|---|---|
| `firedesmoke` | `firedesmoke_full.pt` | Fire, chamber, RealX3D, public haze; default demo | 384 / 96 |
| `firedesmoke-smokebench` | `firedesmoke_smokebench.pt` | SmokeBench; FireDesmoke*, trained only on its training split | 320 / 80 |

Both defaults use horizontal-flip averaging and linear overlap blending,
reflect padding to multiples of 16, original-size output and half-up RGB 8-bit PNG
conversion. Complete checkpoint hashes are in [the registry](../registry/models.json).
The default demo uses the full model even on SmokeBench example inputs.

The separate training program is pending. These cards do not infer unprovided
optimizer settings, seeds or schedules from filenames. Restoration can alter
color or texture and cannot guarantee recovery of fully obscured objects.
