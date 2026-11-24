# Website and README references

The project website adapts the VGGT/Nerfies template. Source revisions and attribution are recorded in [template_sources.json](../site/template_sources.json). Additional references informed presentation without contributing code or scientific assets.

| Reference | Revision | Use in FireDesmoke | Upstream license evidence |
| --- | --- | --- | --- |
| [VGGT website](https://github.com/vgg-t/vgg-t.github.io) | `99b36695b673` | Source for the publication header, resource links, typography and section structure. | [README: CC BY-SA 4.0](https://github.com/vgg-t/vgg-t.github.io/blob/99b36695b67381a2759369df12616bd70cf7d8c4/README.md) |
| [Nerfies website](https://github.com/nerfies/nerfies.github.io) | `657409a62d59` | Original template credited by VGGT; checked for the shared structure and styles. | [README: CC BY-SA 4.0](https://github.com/nerfies/nerfies.github.io/blob/657409a62d59a93163872c0e4921cf651b987810/README.md) |
| [PixelDiT website](https://github.com/PixelDiT/PixelDiT.github.io) | `0920f901008c` | Reference for the resource row and visual-first result presentation; no code or assets copied. | No project-wide license found in the inspected repository tree, root README or homepage. |
| [VGGT model repository](https://github.com/facebookresearch/vggt) | `a288dd0f1478` | README reference: centered paper identity, resource links and a short inference path. No model code or assets copied. | [VGGT License](https://github.com/facebookresearch/vggt/blob/a288dd0f14786c93483e45524328726ab7b1b4ce/LICENSE.txt), distinct from the website license. |
| [Depth Pro repository](https://github.com/apple/ml-depth-pro) | `9e65e4dbe956` | README reference: result teaser, concise setup and explicit reproduction limitations. No code or assets copied. | [Apple license](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/LICENSE). |

FireDesmoke provides its own image-comparison and dataset-table scripts. Upstream analytics, external scripts, 3D viewers and scientific media are not included.

The unchanged **Bulma 0.9.1** stylesheet comes from the VGGT/Nerfies snapshot.
Its MIT notice and [full license](../site/dist/vendor/BULMA-LICENSE.txt) are
included. The adapted template attribution and CC BY-SA 4.0 scope are recorded
in [LICENSE-TEMPLATE.md](../site/LICENSE-TEMPLATE.md); these notices do not
assign a release license to FireDesmoke model code, weights, datasets or figures.
