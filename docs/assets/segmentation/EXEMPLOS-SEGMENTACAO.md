# Segmentation examples

These examples show the same Beans training inputs before and after the
segmentation step. They are illustrative assets for the project documentation,
not an additional experiment input.

| Class | Original source member | Segmented output |
| --- | --- | --- |
| `angular_leaf_spot` | `angular_leaf_spot_train.98.jpg` | `segmented.png` |
| `bean_rust` | `bean_rust_train.212.jpg` | `segmented.png` |
| `healthy` | `healthy_train.265.jpg` | `segmented.png` |

The originals come from the official Beans training archive used by the
preparation pipeline. The segmented files were generated with `make prepare`
and the parameters in `protocol.json`. The complete generated collection stays
local under `artifacts/v1/segmented/`.
