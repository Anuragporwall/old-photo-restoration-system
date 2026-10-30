"""Streamlit interface for Old Photograph Restoration System."""
from __future__ import annotations

import io
import zipfile
from dataclasses import asdict
from datetime import datetime

import cv2
import numpy as np
import streamlit as st

from algorithms import PRESETS, PipelineSettings, RestorationError, automatic_restore, bilinear_resize, enhance_contrast, frequency_filter, gaussian_filter, grayscale, image_metrics, laplacian_enhance, median_filter, safe_restore, spectrum_image, to_display_rgb, unsharp_mask, validate_image

MAX_FILES, MAX_SIZE, MAX_PIXELS = 5, 20 * 1024 * 1024, 20_000_000
ACCEPTED = ["jpg", "jpeg", "png", "bmp", "tif", "tiff"]

st.set_page_config(page_title="Old Photo Restoration", page_icon="▣", layout="wide")
st.markdown("""<style>
 .stApp {background:#0b1020;color:#e6edf8}.block-container{max-width:1450px;padding-top:1.5rem}
 [data-testid="stSidebar"]{background:#10182d}.hero{padding:1.3rem 1.6rem;border:1px solid #283a62;border-radius:18px;background:linear-gradient(120deg,#111b33,#172a46)}
 .hero h1{margin:0;color:#e8f1ff}.hero p{color:#9fb0ca;margin:.35rem 0 0}.small-note{color:#9fb0ca;font-size:.86rem}
 div[data-testid="stMetric"]{background:#111b30;border:1px solid #263b63;padding:10px;border-radius:10px}
 </style>""", unsafe_allow_html=True)


def initialize() -> None:
    defaults = {"photos": {}, "active": None, "custom_presets": {}, "confirm": None}
    for key, value in defaults.items(): st.session_state.setdefault(key, value)


def decode(upload) -> np.ndarray:
    data = np.frombuffer(upload.getvalue(), np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    validate_image(image)
    if image.shape[0] * image.shape[1] > MAX_PIXELS: raise RestorationError("Image exceeds the 20 megapixel safety limit.")
    return image


def add_photo(upload) -> None:
    if upload.name in st.session_state.photos: return
    image = decode(upload)
    st.session_state.photos[upload.name] = {"original": image, "variants": {"Original": image.copy()}, "history": [], "active_variant": "Original", "created": datetime.now().isoformat()}
    st.session_state.active = upload.name


def current():
    photo = st.session_state.photos[st.session_state.active]
    return photo, photo["variants"][photo["active_variant"]]


def save_variant(name: str, image: np.ndarray) -> None:
    photo, _ = current()
    key = name.strip() or f"Variant {len(photo['variants'])}"
    photo["variants"][key] = image
    photo["history"].append(photo["active_variant"])
    photo["active_variant"] = key


def png_bytes(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    if not ok: raise RestorationError("Could not encode the result as PNG.")
    return encoded.tobytes()


def settings_controls() -> PipelineSettings:
    st.sidebar.subheader("Restoration controls")
    preset_names = list(PRESETS) + list(st.session_state.custom_presets)
    selected = st.sidebar.selectbox("Preset", preset_names)
    base = PRESETS.get(selected, st.session_state.custom_presets.get(selected, PipelineSettings()))
    if st.sidebar.button("Load preset"): st.session_state.settings = asdict(base)
    values = st.session_state.get("settings", asdict(base))
    grayscale_option = st.sidebar.toggle("Optional grayscale", values["grayscale"])
    with st.sidebar.expander("Noise and contrast", expanded=True):
        median = st.slider("Median kernel", 1, 11, values["median_kernel"], step=2)
        gaussian = st.slider("Gaussian kernel", 1, 11, values["gaussian_kernel"], step=2)
        sigma = st.slider("Gaussian sigma", 0.1, 3.0, float(values["gaussian_sigma"]), .1)
        clip = st.slider("CLAHE clip limit", .5, 5.0, float(values["clahe_clip"]), .1)
    with st.sidebar.expander("Detail and scale"):
        unsharp = st.slider("Unsharp amount", 0.0, 1.5, float(values["unsharp_amount"]), .05)
        laplace = st.slider("Laplacian strength", 0.0, 1.0, float(values["laplacian_strength"]), .05)
        scale = st.select_slider("Bilinear scale", options=[.5, .75, 1.0, 1.25, 1.5, 2.0, 3.0], value=float(values["scale"]))
    with st.sidebar.expander("Frequency domain"):
        low = st.slider("Low-pass radius (0 = off)", 0, 100, int(values["low_pass_radius"]))
        high = st.slider("High-pass radius (0 = off)", 0, 100, int(values["high_pass_radius"]))
    result = PipelineSettings(grayscale_option, median, gaussian, sigma, clip, 8, unsharp, 1.2, laplace, low, high, scale)
    st.session_state.settings = asdict(result)
    new_name = st.sidebar.text_input("Save settings as session preset")
    if st.sidebar.button("Save custom preset", disabled=not new_name.strip()):
        st.session_state.custom_presets[new_name.strip()] = result
        st.sidebar.success("Session preset saved.")
    return result


def apply_operation(image: np.ndarray, operation: str, settings: PipelineSettings) -> np.ndarray:
    functions = {"Median filter": lambda: median_filter(image, settings.median_kernel), "Gaussian filter": lambda: gaussian_filter(image, settings.gaussian_kernel, settings.gaussian_sigma), "Contrast enhancement": lambda: enhance_contrast(image, settings.clahe_clip, settings.clahe_grid), "Unsharp masking": lambda: unsharp_mask(image, settings.unsharp_sigma, settings.unsharp_amount), "Laplacian enhancement": lambda: laplacian_enhance(image, settings.laplacian_strength), "Low-pass frequency filter": lambda: frequency_filter(image, settings.low_pass_radius, "low"), "High-pass frequency filter": lambda: frequency_filter(image, settings.high_pass_radius, "high"), "Bilinear interpolation": lambda: bilinear_resize(image, settings.scale)}
    return functions[operation]()


def main() -> None:
    initialize()
    st.markdown("<div class='hero'><h1>Old Photograph Restoration System</h1><p>Classical digital image processing. Keep the original intact, explore named variants, and compare every restoration.</p></div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Add up to five photographs (JPG, JPEG, PNG, BMP, TIFF; max 20 MB each)", type=ACCEPTED, accept_multiple_files=True)
    if uploaded:
        if len(uploaded) > MAX_FILES: st.error("Choose no more than five images at once.")
        else:
            for file in uploaded:
                if file.size > MAX_SIZE: st.error(f"{file.name} is larger than 20 MB.")
                else:
                    try: add_photo(file)
                    except RestorationError as exc: st.error(f"{file.name}: {exc}")
    if not st.session_state.photos:
        st.info("Upload a photograph to begin. Processing stays in this browser session and is cleared when the session ends.")
        return
    names = list(st.session_state.photos)
    st.session_state.active = st.selectbox("Photo in this session", names, index=names.index(st.session_state.active))
    settings = settings_controls()
    photo, image = current()
    estimated = round(image.shape[0] * image.shape[1] * settings.scale ** 2 * 3 / 1_000_000, 1)
    if estimated > 60: st.warning(f"Large output expected: about {estimated} MB uncompressed. Reduce scale or remove unused variants if processing is slow.")
    left, right = st.columns([1, 1])
    with left: st.image(to_display_rgb(photo["original"]), caption="Original", use_container_width=True)
    with right: st.image(to_display_rgb(image), caption=f"Current: {photo['active_variant']}", use_container_width=True)
    st.caption("Use the adjacent panels as a side-by-side comparison. The original image is never overwritten.")
    metrics = image_metrics(image)
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics.items()): column.metric(label, value)
    tab_restore, tab_steps, tab_analysis, tab_manage = st.tabs(["Automatic restoration", "Step-by-step", "Analysis", "Variants & downloads"])
    with tab_restore:
        variant_name = st.text_input("New variant name", value="Balanced restoration")
        confirm_large = True
        if estimated > 60: confirm_large = st.checkbox("I understand this may use significant memory")
        if st.button("Preview and apply balanced pipeline", type="primary", disabled=not confirm_large):
            bar, status = st.progress(0), st.empty()
            stages = ["Reducing speckle noise", "Smoothing fine noise", "Recovering local contrast", "Restoring edge detail", "Finalizing restoration"]
            def progress(message): status.write(message); bar.progress(min(100, (stages.index(message) + 1) * 20) if message in stages else 20)
            try:
                result, retried = safe_restore(image, settings, progress)
                save_variant(variant_name, result); bar.progress(100)
                st.success("Restoration completed successfully." if not retried else "Restoration completed successfully with safe settings.")
            except Exception:
                st.error("Restoration could not be completed. Existing results are unchanged; reduce scale or simplify the settings.")
    with tab_steps:
        operation = st.selectbox("Operation", ["Median filter", "Gaussian filter", "Contrast enhancement", "Unsharp masking", "Laplacian enhancement", "Low-pass frequency filter", "High-pass frequency filter", "Bilinear interpolation"])
        step_name = st.text_input("Step variant name", value=operation)
        if st.button("Preview and apply selected step"):
            try: save_variant(step_name, apply_operation(image, operation, settings)); st.success("Step applied.")
            except Exception as exc: st.error(f"Step could not be completed: {exc}")
    with tab_analysis:
        c1, c2 = st.columns(2)
        with c1: st.image(spectrum_image(image), caption="Log-magnitude frequency spectrum", clamp=True, use_container_width=True)
        with c2:
            hist_source = grayscale(image)
            histogram = np.histogram(hist_source.ravel(), bins=256, range=(0, 256))[0]
            st.bar_chart(histogram)
            st.caption("Luminance histogram")
    with tab_manage:
        choice = st.selectbox("Active variant", list(photo["variants"]), index=list(photo["variants"]).index(photo["active_variant"]))
        photo["active_variant"] = choice
        b1, b2, b3 = st.columns(3)
        if b1.button("Undo last variant") and photo["history"]: photo["active_variant"] = photo["history"].pop(); st.rerun()
        if b2.button("Reset to original"): photo["active_variant"] = "Original"; st.rerun()
        delete_variant = b3.checkbox("Confirm delete selected variant")
        if st.button("Delete selected variant", disabled=choice == "Original" or not delete_variant):
            del photo["variants"][choice]; photo["active_variant"] = "Original"; st.rerun()
        filename = st.text_input("PNG filename", value=f"{st.session_state.active.rsplit('.', 1)[0]}_{photo['active_variant']}.png")
        st.download_button("Download current PNG", png_bytes(image), file_name=filename if filename.endswith(".png") else f"{filename}.png", mime="image/png")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for photo_name, entry in st.session_state.photos.items():
                for variant, result in entry["variants"].items(): bundle.writestr(f"{photo_name.rsplit('.',1)[0]}_{variant}.png", png_bytes(result))
        st.download_button("Download all variants as ZIP", archive.getvalue(), file_name="restored_photos.zip", mime="application/zip")
        confirm_photo = st.checkbox("Confirm delete current photo")
        if st.button("Delete current photo", disabled=not confirm_photo):
            del st.session_state.photos[st.session_state.active]; st.session_state.active = next(iter(st.session_state.photos), None); st.rerun()
        confirm_session = st.checkbox("Confirm clear entire session")
        if st.button("Clear session", disabled=not confirm_session): st.session_state.photos = {}; st.session_state.active = None; st.rerun()


if __name__ == "__main__": main()
