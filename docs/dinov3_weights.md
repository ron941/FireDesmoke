# DINOv3 weight compatibility

FireDesmoke uses the official **DINOv3 ViT-L/16, LVD-1689M** encoder.
The author used a Meta-format `.pth` file whose SHA256 begins `7246d841`.
The official Hugging Face distribution uses `model.safetensors`. File hashes
cannot establish equality across these serialization formats.

The verified alternative comes from
[facebook/dinov3-vitl16-pretrain-lvd1689m](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m),
revision `ea8dc2863c51be0a264bab82070e3e8836b02d51`, with source SHA256
`dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179`.
Download requires authorized access under the model's license.

`python scripts/convert_official_dinov3.py --input /path/to/model.safetensors --output /path/to/dinov3_vitl16_lvd1689m_from_official_hf.pth`

The conversion follows the inverse of the
[Transformers conversion](https://github.com/huggingface/transformers/blob/v4.56.2/src/transformers/models/dinov3_vit/convert_dinov3_vit_to_hf.py):

- Rename keys and concatenate Q/K/V projections without changing tensor values or precision.
- Restore the mask-token dimension expected by Meta's implementation.
- Reconstruct the fixed K-bias mask, zero the masked K bias, and reconstruct analytical RoPE periods.

All 415 source tensors are retained. Both official implementations load strictly.
The four normalized feature layers used by FireDesmoke (6, 12, 18, 24) were
compared at 224×224, 320×320, 384×384 and 288×400 with FP32 GPU inference.
The maximum absolute difference was 0.000222; every comparison passed
`atol=0.0003, rtol=0.0003`. These are floating-point implementation differences,
not a claim of byte-identical serialization. See [the audit record](dinov3_equivalence.json).

The runtime accepts the specific verified converted-file hash recorded in
`registry/models.json`; it does not accept arbitrary alternative checkpoints.
The teacher's `model.py` and restoration math remain unchanged.

End-to-end checks used both FireDesmoke checkpoints, 384/320 windows, flip
averaging, a 640×480 image, and a 379×281 image exercising reflect padding.
Swapping only the encoder between official HF and Meta implementations changed
8-bit predictions by at most one intensity level (four comparisons). The
repository inference wrapper and the author's standalone `infer.py` produced
identical 8-bit output for each checkpoint using the same Meta encoder.
See [encoder comparison](dinov3-end-to-end-audit.json) and
[author inference parity](author-inference-parity.json).
