# Old Photograph Restoration System Using Digital Image Processing

## Abstract

Old photographs commonly suffer from fading, low contrast, dust, impulse noise, soft edges, and reduced detail. This project delivers a browser-based restoration system built with Python, Streamlit, OpenCV, and NumPy. The system applies only classical digital image processing techniques: median and Gaussian filtering, local histogram-based contrast enhancement, unsharp masking, Laplacian enhancement, bilinear interpolation, and frequency-domain filtering. It preserves the original image, lets the user create named result variants, and gives visual and numerical feedback to support comparison.

## Objectives

1. Restore moderate photograph degradation without AI or machine learning.
2. Preserve colour by default and offer grayscale processing only when selected.
3. Give users both an automatic balanced pipeline and transparent step-by-step control.
4. Keep multiple photos and multiple variants safely within one temporary session.
5. Prevent avoidable failures through validation, resource limits, confirmation prompts, and safe retry.

## Technology

| Layer | Technology | Role |
| --- | --- | --- |
| User interface | Streamlit | Dark interactive dashboard and browser-session state |
| Image operations | OpenCV | Filtering, colour conversion, interpolation, encoding |
| Frequency processing | NumPy | Two-dimensional fast Fourier transforms and masks |
| Analysis | NumPy / OpenCV | Histogram, luminance, contrast, and sharpness metrics |
| Verification | Pytest | Algorithm and safety checks |

## Methodology

### Input and validation

The system accepts JPG, JPEG, PNG, BMP, and TIFF files. It limits a session to five photographs and every upload to 20 MB. Decoded image dimensions are limited to 20 megapixels. These limits help prevent an upload from exhausting the browser session's memory.

### Spatial-domain restoration

Median filtering removes salt-and-pepper noise while preserving strong edges. Gaussian filtering reduces fine random noise. Contrast Limited Adaptive Histogram Equalization (CLAHE) improves local contrast; for colour images it is applied only to the L component in the CIELAB colour space, retaining chromatic information. Unsharp masking combines the source image with a negative blurred image to improve local detail. The Laplacian operator enhances rapid intensity transitions.

### Frequency-domain restoration

For every channel, the system calculates a 2-D Fourier transform, shifts the low-frequency components to the center, applies a circular low-pass or high-pass mask, and performs the inverse transform. The displayed log-magnitude spectrum helps users relate filter parameters to frequency content.

### Automatic pipeline

The balanced pipeline uses conservative values: median denoising, light Gaussian smoothing, CLAHE, unsharp masking, and Laplacian enhancement. Optional frequency operations and resizing are included only when enabled. An operation is never destructive: the result becomes a separate named variant.

## Safety and reliability

- Original photographs and previously successful variants remain unchanged after an error.
- Large outputs require acknowledgement and a hard 30-megapixel output limit.
- Deleting a variant, photo, or entire session needs an explicit confirmation control.
- When possible, the automatic pipeline retries once with lower-impact settings. The interface shows only the final success or failure result.
- Batch-oriented usage continues independently: an error for one image does not invalidate other photos in the session.
- Custom presets are kept only in the active Streamlit session and are discarded when it ends.

## User workflow

1. Upload one to five accepted photos.
2. Select a photo and choose a built-in or custom session preset.
3. Preview and apply the automatic pipeline, or apply individual steps.
4. Name the variant, compare it with the original, and inspect metrics, histogram, and spectrum.
5. Undo, reset, retain several variants, or export an individual PNG / all variants as a ZIP file.

## Results and evaluation

The sample result in `assets/` illustrates improved local contrast and reduced noise from a simulated faded photo. Classical processing improves visible quality for common low-to-moderate degradation, but cannot truthfully recreate missing objects or severe physical damage. The included automated tests verify image dimensions, colour path shape, spatial filtering, FFT filtering, metrics, retry behavior, and size protection.

## Conclusion

The project demonstrates an explainable restoration workflow using classical digital image processing. The controls expose the relationship between algorithm settings and output while the automatic route provides a safer starting point. The session-only architecture avoids retaining sensitive personal photos beyond the active browser session.

## Future work

Potential extensions include scratch detection based on morphology, illumination correction using background estimation, image-quality scoring, a processing history panel, and formal user-study evaluation. These can be added while keeping the core system free of machine learning.
