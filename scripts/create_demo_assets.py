"""Generate a synthetic faded-photo example and a restored result for documentation."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
assets.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
height, width = 560, 860
y, x = np.mgrid[:height, :width]
base = np.zeros((height, width, 3), np.uint8)
base[:, :, 0] = np.clip(70 + x / 20 + y / 15, 0, 255); base[:, :, 1] = np.clip(55 + x / 13, 0, 255); base[:, :, 2] = np.clip(38 + y / 11, 0, 255)
scene = Image.fromarray(base, "RGB")
draw = ImageDraw.Draw(scene)
draw.rectangle((110, 90, 750, 455), fill=(170, 125, 90)); draw.ellipse((225, 155, 455, 385), fill=(210, 185, 155)); draw.ellipse((470, 200, 640, 370), fill=(135, 92, 60)); draw.text((300, 495), "MEMORIES", fill=(235, 225, 205), font_size=34)
base = np.asarray(scene)
faded = np.clip(base.astype(np.float32) * .48 + 180 * .52, 0, 255).astype(np.uint8)
noise = rng.normal(0, 13, faded.shape).astype(np.int16)
faded = np.clip(faded.astype(np.int16) + noise, 0, 255).astype(np.uint8)
for _ in range(800):
    yy, xx = rng.integers(0, height), rng.integers(0, width)
    faded[yy, xx] = (245, 245, 240)
input_image = Image.fromarray(faded, "RGB")
input_image.save(assets / "sample_faded_input.png")
restored = ImageEnhance.Contrast(input_image.filter(ImageFilter.MedianFilter(3))).enhance(1.45)
restored = restored.filter(ImageFilter.UnsharpMask(radius=2, percent=135, threshold=3))
restored.save(assets / "sample_restored_output.png")
panel = Image.new("RGB", (width * 2, height), "#111827"); panel.paste(input_image, (0, 0)); panel.paste(restored, (width, 0))
labels = ImageDraw.Draw(panel); labels.text((35, 20), "Input", fill="white", font_size=28); labels.text((width + 35, 20), "Restored", fill="white", font_size=28)
panel.save(assets / "sample_comparison.png")
