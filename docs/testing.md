# Testing Documentation

## Scope

Automated tests cover deterministic classical-processing behavior and safety validation. Manual checks cover the Streamlit interaction paths that require a browser session.

## Automated checks

Run `pytest -q` from the project directory.

| Area | Expected result |
| --- | --- |
| Contrast | CLAHE output retains image size and RGB channels |
| Spatial filtering | Median filtering reduces impulse-noise variance |
| Resize protection | Oversized bilinear enlargement is rejected |
| Frequency filtering | A valid low-pass mask returns a same-sized image |
| Retry | Invalid advanced settings fall back to a safe restoration |
| Metrics | Width, height, luminance, contrast, and sharpness are reported |

## Manual acceptance checklist

1. Upload valid and invalid file types, an image over 20 MB, and more than five files.
2. Confirm every image retains colour unless grayscale is enabled.
3. Apply automatic restoration and a separate step; verify named variants persist per photograph.
4. Try a high output scale; verify the warning and confirmation gate appear.
5. Remove a variant, photo, and session only after each confirmation is selected.
6. Download an individual PNG with a changed filename and a ZIP containing every variant.
7. Force an unsuitable frequency radius; verify only a final outcome is presented and earlier results remain.
8. Upload multiple photos, make one operation fail, and verify the remaining photographs stay usable.
