# Sources and distribution

No public FireDesmoke license or
checkpoint download URL is granted here. The 2026-11-16 model and inference code
come from the authors; [delivery hashes](../registry/author_delivery.json) record
provenance. Training and scoring programs are not included in this delivery.

## AdaIR and DINOv3

AdaIR architecture code is obtained from [the official repository](https://github.com/c-yn/AdaIR),
pinned to `ccb8b98e49614e07badd0641e5163fa7635c2f02`. It is kept outside the
tracked package. FireDesmoke provides its trained restoration parameters, so
AdaIR's separate pretrained checkpoint is not downloaded.

DINOv3 code is obtained from [the official repository](https://github.com/facebookresearch/dinov3),
pinned in [the model registry](../registry/models.json). Its ViT-L/16 LVD-1689M
weight requires authorized access under the DINOv3 license. Follow the upstream
license and notices for code and model use; this repository does not redistribute
those weights. [DINOv3 compatibility](dinov3_weights.md) describes the verified
conversion from the official gated Hugging Face distribution.

Third-party packages retain their own licenses. Website images, data, author
weights and the website template have separate distribution terms. See
[asset policy](../registry/asset_policy.json) and [local setup](local_access.md).

## Project-site template and fonts

The project page now adapts the actual header and section structure from
[VGGT's project website](https://github.com/vgg-t/vgg-t.github.io), which credits
[Nerfies](https://github.com/nerfies/nerfies.github.io). The adapted website
structure and `vggt-template.css` retain CC BY-SA 4.0 attribution and modification
notes in [LICENSE-TEMPLATE.md](../site/LICENSE-TEMPLATE.md). This template license
does not apply to FireDesmoke's model, weights, figures or datasets.

Bulma 0.9.1 is served locally with its MIT notice. Google Sans and Noto Sans are
served locally with their OFL license files and source records in
`site/dist/fonts/`. Additional bundled fonts retain their source and license records. The site does not depend on external font or
CDN requests.

[Website references](website_references.md) records template sources and design references. In particular, the
`facebookresearch/vggt` model repository uses its own VGGT License; it must not be
confused with the separate VGGT website template's CC BY-SA license. No VGGT or
Depth Pro model implementation or sample image is incorporated into FireDesmoke.
The GitHub README badges are local SVGs created for this repository.

## Distribution scope

No public FireDesmoke code or weight license is granted here. Dataset permissions and the website-template license are separate from model and checkpoint distribution rights.
