# Validation status

This record applies to the authors' 2026-11-16 AdaIR + DINOv3 delivery.

- Both delivered restoration checkpoints pass the supplied SHA256 checks.
- The repository wrapper and author's standalone inference produce identical
  8-bit outputs in the recorded same-environment tests for both checkpoints:
  [author inference parity](author-inference-parity.json).
- The authorized official Hugging Face DINOv3 distribution was converted to
  the Meta state-dict format with all 415 source tensors preserved. Strict
  loading and four feature resolutions pass the recorded tolerance checks:
  [feature comparison](dinov3_equivalence.json).
- End-to-end HF-versus-Meta encoder checks differ by at most one 8-bit intensity
  level over the recorded four comparisons, including non-multiple-of-16 input:
  [end-to-end comparison](dinov3-end-to-end-audit.json).

These checks establish implementation compatibility on the tested examples, not
bitwise equality on every device or reproduction of entire benchmark tables.
The four CSVs remain author-reported results. Training and scoring programs for
the delivered model are not yet supplied. No full-training or full-dataset
score-reproduction claim is made.

The CLI writes actual checkpoint hashes, inference settings and per-image hashes
to `_run.json`. Automated tests cover image validation, temporary-file isolation,
asset verification and demo contracts. Website and demo deployment checks are
tracked separately from model numerical parity.

## Website and demo checks (2026-11-17)

- 27 Python tests pass, including lossless conversion of all four author CSVs.
  All 228 rendered table rows also match the CSV snapshot, including annotations.
- All six website pages load at 1440- and 390-pixel viewport widths without
  JavaScript errors or horizontal overflow. All 88 tested method-comparison
  states have loaded images with matching dimensions.
- Homepage autoplay, scene changes, divider bounds, label clipping and keyboard
  controls pass the desktop/mobile interaction checks.
- All eight demo thumbnails load on first entry. Selecting an example and then
  uploading a different image works at both viewport widths.
- Real-model upload, restoration and RGB PNG download pass for a 47×33 image
  and a 640×480 fire image. Output dimensions match the displayed processing size.
- 115 website restoration assets were regenerated with the two delivered
  checkpoints and their default inference settings. Run
  `python scripts/check_site_assets.py` to verify hashes, dimensions and settings
  against [the inference manifest](../registry/website_inference.json).

The model definition is unchanged from the delivery. The standalone inference
only adds package-relative import support; its restoration algorithm is unchanged.

The film's 197 restoration assets were regenerated with the same defaults.
Both 66.2-second exports retain 1,986 frames and pass decoded start/end-frame
checks; actual browser playback also wraps successfully. See
[film checks](film-validation.json) and [film inference provenance](../registry/film_inference.json).
