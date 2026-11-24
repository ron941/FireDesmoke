#!/usr/bin/env python3
"""FireDesmoke inference on a folder of images (or one image).

The image is restored in overlapping windows: window size --window (default 384), stride a quarter of the window, linear ramps
over the overlaps (no ramp at the image borders), and each window is averaged with the restoration of its left-right flip.
The image is reflect-padded to a multiple of 16 first and cropped back.  Output: 8-bit PNG with the same name.

  results on our fire recordings, RealX3D, public dehazing sets, indoor burn chamber:  firedesmoke_full.pt,       --window 384
  results on SmokeBench (FireDesmoke*, trained on the SmokeBench training split alone): firedesmoke_smokebench.pt, --window 320

usage:
  python infer.py --weights ../weights/firedesmoke_full.pt --adair-repo PATH/AdaIR --dinov3-repo PATH/dinov3 \
      --dinov3-weights PATH/dinov3_vitl16_pretrain_lvd1689m.pth --input IN_DIR --output OUT_DIR [--window 384] [--no-flip] [--whole]
"""
import argparse
import glob
import os
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from .model import build
except ImportError:  # direct execution
    from model import build

EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def starts(n, t, s):
    v = list(range(0, max(n - t, 0) + 1, s))
    if v[-1] + t < n:
        v.append(n - t)
    return v


def ramp(t, lo_edge, hi_edge, r):
    w = np.ones(t, np.float32)
    if lo_edge:
        w[:r] = (np.arange(r) + 1) / (r + 1)
    if hi_edge:
        w[t - r:] = np.minimum(w[t - r:], (np.arange(r)[::-1] + 1) / (r + 1))
    return w


def run_model(model, xb, flip):
    y = model(xb).float()
    if flip:
        y = 0.5 * (y + torch.flip(model(torch.flip(xb, dims=[3])).float(), dims=[3]))
    return y


@torch.no_grad()
def restore(model, x, window=384, flip=True, whole=False):
    """x: 1, 3, h, w in [0, 1] -> 1, 3, h, w in [0, 1]."""
    if whole:
        return run_model(model, x, flip).clamp(0, 1)
    t, s = window, window // 4
    assert t % 8 == 0, t
    _, _, h, w = x.shape
    xp = F.pad(x, (0, (-w) % 16, 0, (-h) % 16), mode="reflect")
    H, W = xp.shape[2:]
    th, tw = min(t, H), min(t, W)
    sh, sw = max(min(s, th), 8), max(min(s, tw), 8)
    pos = [(y0, x0) for y0 in starts(H, th, sh) for x0 in starts(W, tw, sw)]
    acc = torch.zeros(1, 3, H, W, device=x.device)
    wacc = torch.zeros(1, 1, H, W, device=x.device)
    chunk = max(1, int(16 * (280 / max(th, tw)) ** 2))       # windows per forward pass
    for i in range(0, len(pos), chunk):
        ch = pos[i:i + chunk]
        y = run_model(model, torch.cat([xp[:, :, y0:y0 + th, x0:x0 + tw] for y0, x0 in ch], 0), flip)
        for k, (y0, x0) in enumerate(ch):
            wt = torch.from_numpy(np.outer(ramp(th, y0 > 0, y0 + th < H, th - sh), ramp(tw, x0 > 0, x0 + tw < W, tw - sw))).to(x.device)[None, None]
            acc[:, :, y0:y0 + th, x0:x0 + tw] += y[k:k + 1] * wt
            wacc[:, :, y0:y0 + th, x0:x0 + tw] += wt
    return (acc / wacc)[:, :, :h, :w].clamp(0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--adair-repo", required=True, help="local clone of https://github.com/c-yn/AdaIR")
    ap.add_argument("--dinov3-repo", required=True, help="folder that contains the dinov3 package (clone of facebookresearch/dinov3)")
    ap.add_argument("--dinov3-weights", required=True, help="dinov3_vitl16_pretrain_lvd1689m.pth")
    ap.add_argument("--input", required=True, help="image file or folder")
    ap.add_argument("--output", required=True)
    ap.add_argument("--window", type=int, default=384)
    ap.add_argument("--no-flip", action="store_true")
    ap.add_argument("--whole", action="store_true", help="one forward pass on the whole image (sides must be multiples of 16)")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    model = build(a.weights, a.adair_repo, a.dinov3_repo, a.dinov3_weights, a.device)
    files = [a.input] if os.path.isfile(a.input) else sorted(f for f in glob.glob(os.path.join(a.input, "*")) if f.lower().endswith(EXT))
    os.makedirs(a.output, exist_ok=True)
    t0 = time.time()
    for f in files:
        bgr = cv2.imread(f, cv2.IMREAD_COLOR)
        x = torch.from_numpy(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).to(a.device).permute(2, 0, 1)[None].float() / 255
        y = restore(model, x, a.window, not a.no_flip, a.whole)
        im = (y * 255 + 0.5).byte()[0].permute(1, 2, 0).cpu().numpy()
        cv2.imwrite(os.path.join(a.output, os.path.splitext(os.path.basename(f))[0] + ".png"), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
    print(f"{len(files)} images, {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
