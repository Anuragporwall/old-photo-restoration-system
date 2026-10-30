"""Classical digital image processing operations for photograph restoration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np


class RestorationError(ValueError):
    """Raised when requested processing settings are unsafe or invalid."""


@dataclass(frozen=True)
class PipelineSettings:
    grayscale: bool = False
    median_kernel: int = 3
    gaussian_kernel: int = 3
    gaussian_sigma: float = 0.8
    clahe_clip: float = 2.0
    clahe_grid: int = 8
    unsharp_amount: float = 0.65
    unsharp_sigma: float = 1.2
    laplacian_strength: float = 0.18
    low_pass_radius: int = 0
    high_pass_radius: int = 0
    scale: float = 1.0


PRESETS = {
    "Balanced automatic": PipelineSettings(),
    "Gentle cleanup": PipelineSettings(median_kernel=3, gaussian_kernel=3, gaussian_sigma=0.55, clahe_clip=1.4, unsharp_amount=0.3, laplacian_strength=0.08),
    "Faded print": PipelineSettings(median_kernel=3, gaussian_kernel=3, clahe_clip=3.0, clahe_grid=8, unsharp_amount=0.45, laplacian_strength=0.12),
    "Damaged / noisy": PipelineSettings(median_kernel=5, gaussian_kernel=3, gaussian_sigma=1.0, clahe_clip=1.8, unsharp_amount=0.4, laplacian_strength=0.1),
}


def validate_image(image: np.ndarray) -> None:
    if image is None or image.size == 0:
        raise RestorationError("No image data was supplied.")
    if image.ndim not in (2, 3):
        raise RestorationError("The image must have one or three channels.")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise RestorationError("The image is too small to process.")


def _odd_kernel(value: int) -> int:
    value = int(value)
    if value < 1 or value > 31 or value % 2 == 0:
        raise RestorationError("Filter kernels must be odd numbers from 1 to 31.")
    return value


def to_display_rgb(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image


def grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()


def median_filter(image: np.ndarray, kernel: int) -> np.ndarray:
    return cv2.medianBlur(image, _odd_kernel(kernel))


def gaussian_filter(image: np.ndarray, kernel: int, sigma: float) -> np.ndarray:
    if sigma < 0 or sigma > 20:
        raise RestorationError("Gaussian sigma must be between 0 and 20.")
    kernel = _odd_kernel(kernel)
    return cv2.GaussianBlur(image, (kernel, kernel), sigma)


def enhance_contrast(image: np.ndarray, clip_limit: float, grid_size: int) -> np.ndarray:
    if not 0.1 <= clip_limit <= 10 or not 2 <= grid_size <= 32:
        raise RestorationError("Contrast settings are outside the safe range.")
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    if image.ndim == 2:
        return clahe.apply(image)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def unsharp_mask(image: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    if not 0.1 <= sigma <= 10 or not 0 <= amount <= 3:
        raise RestorationError("Unsharp mask settings are outside the safe range.")
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    return cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)


def laplacian_enhance(image: np.ndarray, strength: float) -> np.ndarray:
    if not 0 <= strength <= 2:
        raise RestorationError("Laplacian strength must be between 0 and 2.")
    laplace = cv2.Laplacian(image, cv2.CV_32F, ksize=3)
    result = image.astype(np.float32) - strength * laplace
    return np.clip(result, 0, 255).astype(np.uint8)


def bilinear_resize(image: np.ndarray, scale: float) -> np.ndarray:
    if not 0.25 <= scale <= 4:
        raise RestorationError("Scale must be between 0.25 and 4.0.")
    height, width = image.shape[:2]
    if height * width * scale * scale > 30_000_000:
        raise RestorationError("The requested output exceeds the 30 megapixel safety limit.")
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_LINEAR)


def frequency_filter(image: np.ndarray, radius: int, mode: str) -> np.ndarray:
    if radius < 1 or radius > min(image.shape[:2]) // 2:
        raise RestorationError("Frequency radius is outside the safe range.")
    channels = [image] if image.ndim == 2 else cv2.split(image)
    output = []
    rows, cols = image.shape[:2]
    y, x = np.ogrid[:rows, :cols]
    center_mask = (x - cols // 2) ** 2 + (y - rows // 2) ** 2 <= radius ** 2
    mask = center_mask.astype(np.float32) if mode == "low" else (~center_mask).astype(np.float32)
    for channel in channels:
        spectrum = np.fft.fftshift(np.fft.fft2(channel))
        restored = np.fft.ifft2(np.fft.ifftshift(spectrum * mask))
        output.append(np.clip(np.abs(restored), 0, 255).astype(np.uint8))
    return output[0] if image.ndim == 2 else cv2.merge(output)


def spectrum_image(image: np.ndarray) -> np.ndarray:
    luminance = grayscale(image)
    spectrum = np.fft.fftshift(np.fft.fft2(luminance))
    magnitude = 20 * np.log(np.abs(spectrum) + 1)
    return cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


def automatic_restore(image: np.ndarray, settings: PipelineSettings, progress: Callable[[str], None] | None = None) -> np.ndarray:
    validate_image(image)
    notify = progress or (lambda _: None)
    result = grayscale(image) if settings.grayscale else image.copy()
    notify("Reducing speckle noise")
    if settings.median_kernel > 1:
        result = median_filter(result, settings.median_kernel)
    notify("Smoothing fine noise")
    if settings.gaussian_kernel > 1:
        result = gaussian_filter(result, settings.gaussian_kernel, settings.gaussian_sigma)
    notify("Recovering local contrast")
    result = enhance_contrast(result, settings.clahe_clip, settings.clahe_grid)
    notify("Restoring edge detail")
    if settings.unsharp_amount:
        result = unsharp_mask(result, settings.unsharp_sigma, settings.unsharp_amount)
    if settings.laplacian_strength:
        result = laplacian_enhance(result, settings.laplacian_strength)
    if settings.low_pass_radius:
        result = frequency_filter(result, settings.low_pass_radius, "low")
    if settings.high_pass_radius:
        result = frequency_filter(result, settings.high_pass_radius, "high")
    if settings.scale != 1:
        result = bilinear_resize(result, settings.scale)
    notify("Finalizing restoration")
    return result


def safe_restore(image: np.ndarray, settings: PipelineSettings, progress: Callable[[str], None] | None = None) -> tuple[np.ndarray, bool]:
    """Run once, then retry a safer balanced configuration when appropriate."""
    try:
        return automatic_restore(image, settings, progress), False
    except (cv2.error, MemoryError, RestorationError):
        safer = PipelineSettings(
            grayscale=settings.grayscale, median_kernel=min(settings.median_kernel, 3),
            gaussian_kernel=min(settings.gaussian_kernel, 3), gaussian_sigma=min(settings.gaussian_sigma, 0.8),
            clahe_clip=min(settings.clahe_clip, 2.0), clahe_grid=min(settings.clahe_grid, 8),
            unsharp_amount=min(settings.unsharp_amount, 0.4), unsharp_sigma=min(settings.unsharp_sigma, 1.0),
            laplacian_strength=min(settings.laplacian_strength, 0.1), scale=min(settings.scale, 1.5),
        )
        return automatic_restore(image, safer, progress), True


def image_metrics(image: np.ndarray) -> dict[str, float | int]:
    luminance = grayscale(image)
    return {"Width": int(image.shape[1]), "Height": int(image.shape[0]), "Mean luminance": round(float(luminance.mean()), 1), "Contrast (std)": round(float(luminance.std()), 1), "Sharpness": round(float(cv2.Laplacian(luminance, cv2.CV_64F).var()), 1)}
