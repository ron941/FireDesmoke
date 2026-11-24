"""FireDesmoke network.

A single RGB image goes through two branches:

  pixel branch    AdaIR (encoder-decoder restoration network); produces the restored image
  foundation      frozen DINOv3 ViT-L/16; patch tokens of blocks 6, 12, 18 and 24 (layer-normalised, 1024 dims each)

Semantic Rectification: two local Transformer blocks (128 dims, 4 heads, 7 x 7 token windows) read the four token layers together
with the 1/4-resolution pixel features sampled at the token centres, and predict a residual update for each token layer
(zero-initialised).  During training the rectified tokens are supervised with the tokens the same frozen encoder extracts from the
clean target; inference uses the input alone.

Local fusion: the rectified tokens are projected to a shared 128-dim map, resampled to the 1/4 and 1/8 grids of the pixel branch
and used as keys and values of a local cross-attention (5 x 5 neighbourhood) whose queries are the pixel features; the fusion
projections are zero-initialised.  The AdaIR decoder then reconstructs the image (residual to the input).

Token geometry: the encoder sees the ImageNet-normalised image, reflect-padded to a multiple of 16; token (i, j) covers pixels
[16 i, 16 i + 16) x [16 j, 16 j + 16).  Token grids and feature grids are aligned by pixel centres (grid_sample,
align_corners=False), so crops and full frames share one convention.

External code and weights (not included here):
  AdaIR    official repository https://github.com/c-yn/AdaIR (file net/model.py is imported from a local clone)
  DINOv3   official repository https://github.com/facebookresearch/dinov3 and its ViT-L/16 LVD-1689M weights
           (dinov3_vitl16_pretrain_lvd1689m.pth)
"""
import importlib.util
import math
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

PATCH = 16
TOKEN_BLOCKS = (5, 11, 17, 23)          # 0-based: blocks 6, 12, 18, 24 of ViT-L
TOKEN_DIM = 1024
IMNET_MEAN, IMNET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def load_adair(adair_repo):
    """AdaIR architecture from a local clone of the official repository (weights come from the FireDesmoke checkpoint)."""
    spec = importlib.util.spec_from_file_location("adair_arch", f"{adair_repo}/net/model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AdaIR(decoder=True)


def load_dinov3(dinov3_repo, dinov3_weights):
    """DINOv3 ViT-L/16 (LVD-1689M).  dinov3_repo: the folder that contains the `dinov3` package."""
    if dinov3_repo not in sys.path:
        sys.path.insert(0, dinov3_repo)
    from dinov3.hub.backbones import Weights, dinov3_vitl16
    m = dinov3_vitl16(pretrained=False, weights=Weights.LVD1689M)
    m.load_state_dict(torch.load(dinov3_weights, map_location="cpu", weights_only=True))
    return m.eval()


def resample_tokens(Z, H, W, stride, patch=PATCH):
    """Z: B, C, h, w token grid -> B, C, H // stride, W // stride, sampled at the pixel centres of a stride-`stride` grid."""
    B, C, h, w = Z.shape
    Hs, Ws = H // stride, W // stride
    ys = (torch.arange(Hs, device=Z.device, dtype=torch.float32) + 0.5) * stride
    xs = (torch.arange(Ws, device=Z.device, dtype=torch.float32) + 0.5) * stride
    gy = (ys / patch) / h * 2 - 1
    gx = (xs / patch) / w * 2 - 1
    grid = torch.stack(torch.meshgrid(gy, gx, indexing="ij")[::-1], -1)[None].expand(B, Hs, Ws, 2)
    return F.grid_sample(Z, grid.to(Z.dtype), mode="bilinear", padding_mode="border", align_corners=False)


def sample_at_tokens(Fs, h, w, stride, patch=PATCH):
    """Fs: B, C, Hs, Ws on a stride-`stride` grid -> B, C, h, w sampled at the token centres."""
    B, C, Hs, Ws = Fs.shape
    ys = (torch.arange(h, device=Fs.device, dtype=torch.float32) * patch + patch / 2) / stride
    xs = (torch.arange(w, device=Fs.device, dtype=torch.float32) * patch + patch / 2) / stride
    grid = torch.stack(torch.meshgrid(ys / Hs * 2 - 1, xs / Ws * 2 - 1, indexing="ij")[::-1], -1)[None].expand(B, h, w, 2)
    return F.grid_sample(Fs, grid.to(Fs.dtype), mode="bilinear", padding_mode="border", align_corners=False)


class LocalBlock(nn.Module):
    """Windowed (k x k tokens) multi-head self-attention + depthwise conv + MLP on a token grid (pre-norm)."""

    def __init__(self, d=128, heads=4, win=7):
        super().__init__()
        self.h, self.win = heads, win
        self.n1 = nn.GroupNorm(1, d)
        self.qkv = nn.Conv2d(d, 3 * d, 1)
        self.proj = nn.Conv2d(d, d, 1)
        self.dw = nn.Conv2d(d, d, 3, padding=1, groups=d)
        self.n2 = nn.GroupNorm(1, d)
        self.mlp = nn.Sequential(nn.Conv2d(d, 2 * d, 1), nn.GELU(), nn.Conv2d(2 * d, d, 1))

    def forward(self, x):
        B, C, h, w = x.shape
        k = self.win
        hd = C // self.h
        q, kk, v = self.qkv(self.n1(x)).chunk(3, 1)
        pad = k // 2
        Kn = F.unfold(F.pad(kk, (pad, pad, pad, pad), mode="replicate"), k).view(B, self.h, hd, k * k, h * w)
        Vn = F.unfold(F.pad(v, (pad, pad, pad, pad), mode="replicate"), k).view(B, self.h, hd, k * k, h * w)
        qq = q.view(B, self.h, hd, 1, h * w)
        att = ((qq * Kn).sum(2, keepdim=True) / math.sqrt(hd)).softmax(3)
        out = (att * Vn).sum(3).view(B, C, h, w)
        x = x + self.proj(out) + self.dw(x)
        return x + self.mlp(self.n2(x))


class LocalFusion(nn.Module):
    """Pixel features + projection of a local cross-attention to the rectified tokens (k x k neighbourhood)."""

    def __init__(self, c, d=128, heads=4, k=5):
        super().__init__()
        self.h, self.k = heads, k
        self.q = nn.Conv2d(c, d, 1)
        self.kv = nn.Conv2d(d, 2 * d, 1)
        self.nq = nn.GroupNorm(1, c)
        self.p = nn.Conv2d(d, c, 1)
        nn.init.zeros_(self.p.weight)
        nn.init.zeros_(self.p.bias)

    def forward(self, Fs, Zs):
        B, C, H, W = Fs.shape
        d = self.q.out_channels
        hd = d // self.h
        k = self.k
        pad = k // 2
        q = self.q(self.nq(Fs)).view(B, self.h, hd, 1, H * W)
        kk, v = self.kv(Zs).chunk(2, 1)
        Kn = F.unfold(F.pad(kk, (pad, pad, pad, pad), mode="replicate"), k).view(B, self.h, hd, k * k, H * W)
        Vn = F.unfold(F.pad(v, (pad, pad, pad, pad), mode="replicate"), k).view(B, self.h, hd, k * k, H * W)
        att = ((q * Kn).sum(2, keepdim=True) / math.sqrt(hd)).softmax(3)
        return Fs + self.p((att * Vn).sum(3).view(B, d, H, W))


class SemanticRectification(nn.Module):
    """Residual updates of the four token layers, predicted from the tokens and the pixel features at the token centres."""

    def __init__(self, dz=TOKEN_DIM, nl=4, d=128, cpix=192, blocks=2):
        super().__init__()
        self.inp = nn.Conv2d(nl * dz, d, 1)
        self.pix = nn.Conv2d(cpix, d, 1)
        self.blocks = nn.Sequential(*[LocalBlock(d) for _ in range(blocks)])
        self.up = nn.ModuleList([nn.Conv2d(d, dz, 1) for _ in range(nl)])
        for u in self.up:
            nn.init.zeros_(u.weight)
            nn.init.zeros_(u.bias)
        self.kv_proj = nn.Conv2d(nl * dz, d, 1)          # rectified tokens -> the 128-dim fusion space

    def forward(self, tokens, pixel_at_tokens):
        hidden = self.blocks(self.inp(torch.cat(tokens, 1)) + self.pix(pixel_at_tokens))
        rectified = [z + u(hidden) for z, u in zip(tokens, self.up)]
        return rectified, self.kv_proj(torch.cat(rectified, 1))


class FireDesmoke(nn.Module):
    def __init__(self, adair_repo, dinov3_repo, dinov3_weights):
        super().__init__()
        self.pixel = load_adair(adair_repo)
        self.encoder = load_dinov3(dinov3_repo, dinov3_weights)
        for p in self.encoder.parameters():
            p.requires_grad_(False)
        self.rectification = SemanticRectification(dz=TOKEN_DIM, cpix=192)
        self.fusion4 = LocalFusion(192)                  # 1/4 resolution (AdaIR encoder level 3)
        self.fusion8 = LocalFusion(384)                  # 1/8 resolution (AdaIR latent)
        self.register_buffer("mean", torch.tensor(IMNET_MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(IMNET_STD).view(1, 3, 1, 1))

    def train(self, mode=True):
        super().train(mode)
        self.encoder.eval()                              # the foundation encoder is always frozen
        return self

    @torch.no_grad()
    def tokens(self, img):
        """img: B, 3, H, W sRGB in [0, 1] -> four tensors B, 1024, ceil(H / 16), ceil(W / 16)."""
        B, _, H, W = img.shape
        ph, pw = (PATCH - H % PATCH) % PATCH, (PATCH - W % PATCH) % PATCH
        x = (img - self.mean) / self.std
        x = F.pad(x, (0, pw, 0, ph), mode="reflect") if (ph or pw) else x
        with torch.autocast(img.device.type, enabled=False):
            return [o.float() for o in self.encoder.get_intermediate_layers(x.float(), n=list(TOKEN_BLOCKS), reshape=True, norm=True)]

    def forward(self, img, clean=None, return_aux=False):
        """img: B, 3, H, W in [0, 1] (H, W multiples of 8) -> restored image.
        clean (training only): the clean target, whose tokens supervise the rectified tokens (returned in aux)."""
        m = self.pixel
        B, _, H, W = img.shape
        aux = {}
        e1 = m.encoder_level1(m.patch_embed(img))
        e2 = m.encoder_level2(m.down1_2(e1))
        e3 = m.encoder_level3(m.down2_3(e2))
        lat = m.latent(m.down3_4(e3))
        tok = self.tokens(img)
        h, w = tok[0].shape[-2:]
        pix = sample_at_tokens(F.avg_pool2d(e3, 3, 1, 1, count_include_pad=False), h, w, 4)
        rectified, kv = self.rectification(tok, pix)
        aux["rectified_tokens"] = rectified
        if clean is not None:
            aux["clean_target_tokens"] = self.tokens(clean)
        e3 = self.fusion4(e3, resample_tokens(kv, H, W, 4))
        lat = self.fusion8(lat, resample_tokens(kv, H, W, 8))

        def fre(f, x):                                   # AdaIR's frequency modules use the FFT: keep them in float32
            with torch.autocast(img.device.type, enabled=False):
                return f(img.float(), x.float())

        d3 = m.decoder_level3(m.reduce_chan_level3(torch.cat([m.up4_3(fre(m.fre1, lat)), e3], 1)))
        d2 = m.decoder_level2(m.reduce_chan_level2(torch.cat([m.up3_2(fre(m.fre2, d3)), e2], 1)))
        d1 = m.refinement(m.decoder_level1(torch.cat([m.up2_1(fre(m.fre3, d2)), e1], 1)))
        out = m.output(d1) + img
        return (out, aux) if return_aux else out


def rectification_loss(rectified, target):
    """Mean over the four layers of [1 - cosine similarity] + 0.1 smooth-L1 between layer-normalised tokens."""
    tot = 0.0
    for a, b in zip(rectified, target):
        tot = tot + (1 - F.cosine_similarity(a, b, dim=1)).mean()
        an = F.layer_norm(a.permute(0, 2, 3, 1), (a.shape[1],))
        bn = F.layer_norm(b.permute(0, 2, 3, 1), (b.shape[1],))
        tot = tot + 0.1 * F.smooth_l1_loss(an, bn)
    return tot / len(rectified)


def build(weights, adair_repo, dinov3_repo, dinov3_weights, device="cuda"):
    """FireDesmoke with a released checkpoint (firedesmoke_full.pt or firedesmoke_smokebench.pt), in eval mode."""
    model = FireDesmoke(adair_repo, dinov3_repo, dinov3_weights)
    state = torch.load(weights, map_location="cpu", weights_only=True)
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not unexpected and all(k.startswith("encoder.") for k in missing), (unexpected[:4], [k for k in missing if not k.startswith("encoder.")][:4])
    return model.to(device).eval()
