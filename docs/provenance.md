# Model and result provenance

The authoritative delivery is the authors' 2026-11-16 package. Exact delivered
file hashes are recorded in [`registry/author_delivery.json`](../registry/author_delivery.json).
The network definition is preserved as supplied; the inference file only adapts
its import for package and standalone use. Restoration math is unchanged.

The two checkpoint hashes, pinned AdaIR and DINOv3 source revisions, and accepted
DINOv3 weight identities are in [`registry/models.json`](../registry/models.json).
See [DINOv3 compatibility](dinov3_weights.md) for the authorized official HF
serialization conversion and its measured numerical limits.

Four author CSVs provide the displayed quantitative results. Their values are
not relabeled as locally reproduced scores. New prediction manifests record the
actual model, inference configuration, input/output hashes and processing sizes.
Training and scoring code for this architecture await separate author delivery.

See [validation](validation.md) for checks actually performed and
[third-party notes](third_party.md) for distribution scope.
