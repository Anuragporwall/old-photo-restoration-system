import numpy as np
import pytest

from algorithms import PipelineSettings, RestorationError, automatic_restore, bilinear_resize, enhance_contrast, frequency_filter, image_metrics, median_filter, safe_restore


def sample_image():
    x = np.tile(np.linspace(20, 220, 80, dtype=np.uint8), (60, 1))
    return np.dstack((x, np.flipud(x), x))


def test_contrast_preserves_colour_shape():
    image = sample_image()
    assert enhance_contrast(image, 2.0, 8).shape == image.shape


def test_median_filter_reduces_impulse_noise():
    image = sample_image()
    noisy = image.copy(); noisy[10, 10] = (255, 255, 255)
    assert median_filter(noisy, 3)[10, 10, 0] < noisy[10, 10, 0]


def test_bilinear_limit_is_protected():
    with pytest.raises(RestorationError): bilinear_resize(np.zeros((3000, 3000, 3), np.uint8), 3.0)


def test_frequency_filter_shape():
    image = sample_image()
    assert frequency_filter(image, 10, "low").shape == image.shape


def test_safe_restore_retries_invalid_radius():
    image = sample_image()
    result, retried = safe_restore(image, PipelineSettings(low_pass_radius=999))
    assert result.shape == image.shape and retried


def test_metrics_include_dimensions():
    metrics = image_metrics(sample_image())
    assert metrics["Width"] == 80 and metrics["Height"] == 60
