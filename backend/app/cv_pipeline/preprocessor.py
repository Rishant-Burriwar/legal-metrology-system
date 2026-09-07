"""
OpenCV Preprocessing Pipeline — Legal Metrology Label Inspector
==============================================================
Stages:
  1. Conditional noise-aware denoise
  2. Auto-deblur (Wiener deconvolution)
  3. Deskew + Perspective rectification
  4. Label region detection (contour → GrabCut fallback → border-trim)
  5. Text-region segmentation via MSER (focus OCR on text-dense zones)
  6. 8 preprocessing variants for adaptive multi-pass OCR:
       A — Balanced CLAHE + Unsharp (standard labels)
       B — Illumination normalized + Bilateral + Morphological closing (shadows/glare)
       C — 2× Bicubic upscale + CLAHE + Sharpen (small text)
       D — Otsu/Adaptive binary (max text/bg separation)
       E — 2.5× upscale + Bilateral + CLAHE (micro-text)
       F — Inverted binary (embossed/debossed text on dark labels)
       G — Morphological top-hat transform (bright text on uneven illumination)
       H — Super contrast stretch + CLAHE (foil/metallic labels)
"""

import os
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from app.core.config import settings


# ---------------------------------------------------------------------------
# Noise estimation & denoising
# ---------------------------------------------------------------------------

def estimate_noise_level(gray: np.ndarray) -> float:
    """Estimate image noise standard deviation via high-pass residual."""
    blurred = cv2.medianBlur(gray, 3)
    diff = cv2.absdiff(gray, blurred)
    return float(np.std(diff))


def conditional_denoise(gray: np.ndarray) -> np.ndarray:
    """
    Noise-aware denoising: only denoise when noise is actually present.
    Uses gentle parameters to preserve text edges on clean images.
    """
    noise_std = estimate_noise_level(gray)

    if noise_std > 18.0:
        return cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    elif noise_std > 12.0:
        return cv2.fastNlMeansDenoising(gray, None, h=5, templateWindowSize=7, searchWindowSize=21)
    else:
        return gray


# ---------------------------------------------------------------------------
# Wiener deconvolution & auto-deblur
# ---------------------------------------------------------------------------

def wiener_deconvolution(gray: np.ndarray, kernel_size: int = 5, noise_power: float = 0.01) -> np.ndarray:
    """
    Wiener deconvolution to restore frequency content lost to blur.
    Uses an estimated Gaussian PSF (point spread function).
    """
    h, w = gray.shape[:2]

    psf = cv2.getGaussianKernel(kernel_size, -1)
    psf = psf @ psf.T

    psf_padded = np.zeros((h, w), dtype=np.float64)
    kh, kw = psf.shape
    psf_padded[:kh, :kw] = psf
    psf_padded = np.roll(psf_padded, -kh // 2, axis=0)
    psf_padded = np.roll(psf_padded, -kw // 2, axis=1)

    img_fft = np.fft.fft2(gray.astype(np.float64))
    psf_fft = np.fft.fft2(psf_padded)

    psf_conj = np.conj(psf_fft)
    psf_power = np.abs(psf_fft) ** 2
    wiener_filter = psf_conj / (psf_power + noise_power)

    restored_fft = img_fft * wiener_filter
    restored = np.real(np.fft.ifft2(restored_fft))
    restored = np.clip(restored, 0, 255).astype(np.uint8)
    return restored


def auto_deblur(gray: np.ndarray) -> np.ndarray:
    """
    Detect blur severity and apply Wiener deconvolution if needed.
    Uses Laplacian variance to estimate blur level.
    """
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if lap_var >= settings.DEBLUR_THRESHOLD:
        return gray

    if lap_var < settings.BLUR_THRESHOLD:
        restored = wiener_deconvolution(gray, kernel_size=7, noise_power=0.005)
    else:
        blur_ratio = 1.0 - (lap_var / settings.DEBLUR_THRESHOLD)
        kernel_size = max(3, min(9, int(3 + blur_ratio * 6)))
        if kernel_size % 2 == 0:
            kernel_size += 1
        restored = wiener_deconvolution(gray, kernel_size=kernel_size, noise_power=0.008)

    restored = unsharp_mask(restored, sigma=0.8, strength=1.0)
    return restored


# ---------------------------------------------------------------------------
# Deskew & perspective rectification
# ---------------------------------------------------------------------------

def deskew_image(gray_img: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detect skew angle and rotate image to straighten it."""
    thresh = cv2.adaptiveThreshold(
        gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6
    )

    pts = np.column_stack(np.where(thresh > 0))
    if len(pts) < 100:
        return gray_img, 0.0

    rect = cv2.minAreaRect(pts)
    angle = rect[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5 or abs(angle) > 45.0:
        return gray_img, 0.0

    (h, w) = gray_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated, angle


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order coordinates: [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def rectify_perspective(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Perspective transform to straighten 4-point quadrilateral label."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_w = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_h = max(int(height_a), int(height_b))

    if max_w < 50 or max_h < 50:
        return img

    dst = np.array([
        [0, 0],
        [max_w - 1, 0],
        [max_w - 1, max_h - 1],
        [0, max_h - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (max_w, max_h), flags=cv2.INTER_CUBIC)
    return warped


# ---------------------------------------------------------------------------
# Label region detection
# ---------------------------------------------------------------------------

def trim_blank_borders(img: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """
    Fallback ROI: trim blank/uniform borders using edge density.
    Useful when contour-based label detection fails (full-frame labels).
    """
    h, w = gray.shape[:2]
    if h < 100 or w < 100:
        return img

    edges = cv2.Canny(gray, 30, 100)

    row_sums = np.sum(edges > 0, axis=1)
    col_sums = np.sum(edges > 0, axis=0)

    row_thresh = max(5, w * 0.01)
    col_thresh = max(5, h * 0.01)

    active_rows = np.where(row_sums > row_thresh)[0]
    active_cols = np.where(col_sums > col_thresh)[0]

    if len(active_rows) < 10 or len(active_cols) < 10:
        return img

    y1 = max(0, active_rows[0] - 5)
    y2 = min(h, active_rows[-1] + 5)
    x1 = max(0, active_cols[0] - 5)
    x2 = min(w, active_cols[-1] + 5)

    if (y2 - y1) < 0.5 * h or (x2 - x1) < 0.5 * w:
        return img

    return img[y1:y2, x1:x2]


def grabcut_foreground_extraction(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Use GrabCut to separate the label/packaging from the background.
    Useful when the label is placed on a table or held in hand.
    Returns cropped foreground or None if extraction is not helpful.
    """
    h, w = img.shape[:2]
    if h < 80 or w < 80:
        return None

    try:
        mask = np.zeros(img.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        # Use center 70% of image as probable foreground rectangle
        margin_h = int(h * 0.1)
        margin_w = int(w * 0.1)
        rect = (margin_w, margin_h, w - 2 * margin_w, h - 2 * margin_h)

        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        fg_mask = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

        # Find bounding box of foreground
        rows = np.any(fg_mask > 0, axis=1)
        cols = np.any(fg_mask > 0, axis=0)
        if not np.any(rows) or not np.any(cols):
            return None

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        # Only crop if it removes meaningful border area
        crop_h = rmax - rmin
        crop_w = cmax - cmin
        if crop_h < 0.3 * h or crop_w < 0.3 * w:
            return None
        if crop_h > 0.95 * h and crop_w > 0.95 * w:
            return None  # GrabCut selected almost everything — not useful

        # Add 2% padding
        pad_r = int(h * 0.02)
        pad_c = int(w * 0.02)
        y1 = max(0, rmin - pad_r)
        y2 = min(h, rmax + pad_r)
        x1 = max(0, cmin - pad_c)
        x2 = min(w, cmax + pad_c)

        return img[y1:y2, x1:x2]
    except Exception:
        return None


def detect_and_crop_label(img: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """
    Detect largest rectangular/quadrilateral contour representing the label and crop.
    Fallback chain: contour detection → GrabCut foreground → border trimming.

    Improvements over original:
    - Tries multiple Canny thresholds (adaptive to image contrast)
    - Uses Hough line-based rectangle detection for parallelogram labels
    - GrabCut foreground extraction as secondary fallback before border trim
    """
    h_img, w_img = img.shape[:2]
    total_area = h_img * w_img

    # --- Attempt 1: Multi-threshold contour detection ---
    best_crop = None
    max_area = 0

    # Try multiple threshold pairs for different label contrasts
    canny_params = [(30, 150), (50, 200), (20, 80)]

    for canny_low, canny_high in canny_params:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, canny_low, canny_high)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edged, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
            area = cv2.contourArea(c)
            if area < 0.05 * total_area:
                continue

            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)

            # Accept quadrilateral contours — try perspective rectification
            if len(approx) == 4 and area > max_area:
                pts = approx.reshape(4, 2).astype(np.float32)
                try:
                    rectified = rectify_perspective(img, pts)
                    rh, rw = rectified.shape[:2]
                    if rw > 0.20 * w_img and rh > 0.20 * h_img:
                        best_crop = rectified
                        max_area = area
                        continue
                except Exception:
                    pass

            # Bounding box fallback for 3–10 sided polygons
            if 3 <= len(approx) <= 10 and area > max_area:
                x, y, w, h = cv2.boundingRect(c)
                pad_x = int(0.02 * w)
                pad_y = int(0.02 * h)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(w_img, x + w + pad_x)
                y2 = min(h_img, y + h + pad_y)

                if (x2 - x1) > 0.25 * w_img or (y2 - y1) > 0.25 * h_img:
                    best_crop = img[y1:y2, x1:x2]
                    max_area = area

        if best_crop is not None:
            break  # Found a good crop with this threshold pair

    if best_crop is not None:
        return best_crop

    # --- Attempt 2: GrabCut foreground extraction ---
    gc_crop = grabcut_foreground_extraction(img)
    if gc_crop is not None:
        return gc_crop

    # --- Attempt 3: Edge-density border trim ---
    return trim_blank_borders(img, gray)


# ---------------------------------------------------------------------------
# Text region segmentation (MSER)
# ---------------------------------------------------------------------------

def extract_text_regions(gray: np.ndarray, bgr: np.ndarray) -> List[np.ndarray]:
    """
    Use MSER (Maximally Stable Extremal Regions) to detect text-dense zones.
    Returns a list of cropped sub-images focused on text areas.
    These crops are used by the OCR to avoid wasting attention on graphics/logos.

    If MSER finds no significant regions, returns [bgr] (full image fallback).
    """
    h, w = gray.shape[:2]

    try:
        mser = cv2.MSER_create(
            _delta=5,
            _min_area=30,
            _max_area=int(h * w * 0.05),  # At most 5% of image per region
            _max_variation=0.25,
        )
        regions, _ = mser.detectRegions(gray)
    except Exception:
        return [bgr]

    if not regions:
        return [bgr]

    # Collect bounding boxes of all MSER regions
    bboxes = []
    for region in regions:
        x, y, rw, rh = cv2.boundingRect(region.reshape(-1, 1, 2))
        # Filter out too-small or too-large regions
        if rw < 8 or rh < 8:
            continue
        if rw > 0.8 * w or rh > 0.8 * h:
            continue
        bboxes.append((x, y, x + rw, y + rh))

    if not bboxes:
        return [bgr]

    # Cluster overlapping bounding boxes into text-zone blocks
    merged = _merge_overlapping_boxes(bboxes, gap=10)

    # Keep only zones that are large enough to contain meaningful text
    crops = []
    for (x1, y1, x2, y2) in merged:
        zone_w = x2 - x1
        zone_h = y2 - y1
        if zone_w < 30 or zone_h < 10:
            continue

        # Add 5px padding
        px1 = max(0, x1 - 5)
        py1 = max(0, y1 - 5)
        px2 = min(w, x2 + 5)
        py2 = min(h, y2 + 5)

        crops.append(bgr[py1:py2, px1:px2])

    if not crops:
        return [bgr]

    # Always include the full image as the first "region" (baseline pass)
    crops.insert(0, bgr)
    return crops[:6]  # Cap at 6 regions to keep processing fast


def _merge_overlapping_boxes(
    boxes: List[Tuple[int, int, int, int]], gap: int = 10
) -> List[Tuple[int, int, int, int]]:
    """Merge overlapping or nearby bounding boxes."""
    if not boxes:
        return []

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged = [boxes[0]]

    for x1, y1, x2, y2 in boxes[1:]:
        mx1, my1, mx2, my2 = merged[-1]
        # Check overlap with gap tolerance
        if x1 <= mx2 + gap and y1 <= my2 + gap and x2 >= mx1 - gap and y2 >= my1 - gap:
            merged[-1] = (min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2))
        else:
            merged.append((x1, y1, x2, y2))

    return merged


# ---------------------------------------------------------------------------
# Image enhancement utilities
# ---------------------------------------------------------------------------

def normalize_illumination(gray: np.ndarray) -> np.ndarray:
    """Correct non-uniform illumination using division normalization."""
    dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
    return norm


def unsharp_mask(image: np.ndarray, sigma: float = 1.0, strength: float = 1.5) -> np.ndarray:
    """Enhance edge sharpness for small packaging text."""
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    return sharpened


def super_contrast_stretch(gray: np.ndarray) -> np.ndarray:
    """
    Aggressive contrast stretching for foil/metallic labels.
    Clips bottom/top 2% of histogram and stretches to full [0, 255] range.
    """
    p2 = np.percentile(gray, 2)
    p98 = np.percentile(gray, 98)
    if p98 - p2 < 10:
        return gray  # Already maximal contrast

    stretched = np.clip((gray.astype(np.float32) - p2) * (255.0 / (p98 - p2)), 0, 255).astype(np.uint8)
    return stretched


# ---------------------------------------------------------------------------
# 8-Variant preprocessing generator
# ---------------------------------------------------------------------------

def generate_preprocessing_variants(cropped_bgr: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Generate 8 preprocessed image variants for adaptive multi-pass OCR.

    Variant A — Balanced CLAHE + Unsharp (standard labels)
    Variant B — Illumination normalized + Bilateral + Morphological closing (shadows/glare)
    Variant C — 2× Bicubic upscale + CLAHE + Sharpen (small text)
    Variant D — Otsu/Adaptive binary (max text/bg separation)
    Variant E — 2.5× upscale + Bilateral + CLAHE (micro-text)
    Variant F — Inverted binary (embossed/debossed text on dark labels)
    Variant G — Morphological top-hat transform (bright text, uneven illumination)
    Variant H — Super contrast stretch + CLAHE (foil/metallic labels)
    """
    cropped_gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    h, w = cropped_gray.shape[:2]

    # Base: auto-deblur on grayscale
    deblurred_gray = auto_deblur(cropped_gray)

    # --- Variant A: Balanced CLAHE + Unsharp ---
    clahe_a = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    enhanced_a = clahe_a.apply(deblurred_gray)
    variant_a = unsharp_mask(enhanced_a, sigma=1.0, strength=1.2)

    # --- Variant B: Illumination normalized + Bilateral + Morphological closing ---
    norm_gray = normalize_illumination(deblurred_gray)
    denoised_b = cv2.bilateralFilter(norm_gray, d=9, sigmaColor=50, sigmaSpace=50)
    clahe_b = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_b = clahe_b.apply(denoised_b)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    variant_b = cv2.morphologyEx(enhanced_b, cv2.MORPH_CLOSE, close_kernel)

    # --- Variant C: 2× Bicubic upscale + CLAHE + Sharpen ---
    upscale_c = 2.0
    upscaled_c = cv2.resize(
        deblurred_gray, (int(w * upscale_c), int(h * upscale_c)), interpolation=cv2.INTER_CUBIC
    )
    clahe_c = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced_c = clahe_c.apply(upscaled_c)
    variant_c = unsharp_mask(enhanced_c, sigma=1.2, strength=1.5)

    # --- Variant D: Adaptive Binary (Otsu vs Adaptive Gaussian, pick better) ---
    clahe_d = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_d = clahe_d.apply(deblurred_gray)
    _, otsu_binary = cv2.threshold(enhanced_d, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive_binary = cv2.adaptiveThreshold(
        enhanced_d, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    otsu_ratio = float(np.sum(otsu_binary > 127)) / float(otsu_binary.size)
    variant_d = otsu_binary if 0.15 < otsu_ratio < 0.85 else adaptive_binary

    # --- Variant E: 2.5× upscale + Bilateral + CLAHE (micro-text) ---
    upscale_e = 2.5
    upscaled_e = cv2.resize(
        deblurred_gray, (int(w * upscale_e), int(h * upscale_e)), interpolation=cv2.INTER_CUBIC
    )
    bilateral_e = cv2.bilateralFilter(upscaled_e, d=7, sigmaColor=40, sigmaSpace=40)
    clahe_e = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced_e = clahe_e.apply(bilateral_e)
    variant_e = unsharp_mask(enhanced_e, sigma=0.8, strength=1.0)

    # --- Variant F: Inverted binary (embossed/debossed text on dark labels) ---
    # First run adaptive threshold, then invert — recovers light-on-dark text
    adaptive_f = cv2.adaptiveThreshold(
        deblurred_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 6
    )
    # Apply morphological opening to remove noise specks
    open_kernel_f = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    variant_f = cv2.morphologyEx(adaptive_f, cv2.MORPH_OPEN, open_kernel_f)

    # --- Variant G: Morphological top-hat (bright text on uneven bg) ---
    # Top-hat = original - morphological opening
    # This extracts bright features smaller than the structuring element
    tophat_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
    tophat = cv2.morphologyEx(deblurred_gray, cv2.MORPH_TOPHAT, tophat_kernel)
    # Enhance and threshold the top-hat result
    clahe_g = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    variant_g = clahe_g.apply(tophat)

    # --- Variant H: Super contrast stretch + CLAHE (foil/metallic labels) ---
    stretched_h = super_contrast_stretch(deblurred_gray)
    clahe_h = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(6, 6))
    enhanced_h = clahe_h.apply(stretched_h)
    variant_h = unsharp_mask(enhanced_h, sigma=0.8, strength=0.8)

    return {
        "variant_a": variant_a,
        "variant_b": variant_b,
        "variant_c": variant_c,
        "variant_d": variant_d,
        "variant_e": variant_e,
        "variant_f": variant_f,
        "variant_g": variant_g,
        "variant_h": variant_h,
    }


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def process_label_image(
    image_bytes: bytes,
    storage_dir: str,
    inspection_id: int,
    image_index: int = 0,
) -> Tuple[str, str, np.ndarray, Dict[str, np.ndarray]]:
    """
    Complete OpenCV preprocessing pipeline for a single image:

    1. Decode & save original
    2. Conditional noise-aware denoise
    3. Deskew & perspective rectification
    4. Label region detection & crop (contour → GrabCut → border-trim)
    5. Generate 8 preprocessing variants (A-H) for adaptive OCR
    6. Save cropped image to storage

    Args:
        image_bytes:    Raw image bytes from upload
        storage_dir:    Directory to write processed images
        inspection_id:  DB inspection record ID (for filenames)
        image_index:    0-based index when processing multiple images per inspection

    Returns:
        (orig_filename, cropped_filename, enhanced_gray, variants_dict)
    """
    os.makedirs(storage_dir, exist_ok=True)

    np_arr = np.frombuffer(image_bytes, np.uint8)
    original_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if original_bgr is None:
        raise ValueError("Could not decode image from provided bytes.")

    # Save original
    suffix = f"_{image_index}" if image_index > 0 else ""
    orig_filename = f"inspection_{inspection_id}{suffix}_orig.png"
    orig_path = os.path.join(storage_dir, orig_filename)
    cv2.imwrite(orig_path, original_bgr)

    # 1. Grayscale
    gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Conditional denoise
    denoised = conditional_denoise(gray)

    # 3. Deskew
    deskewed_gray, angle = deskew_image(denoised)
    if abs(angle) > 0.5:
        (h, w) = original_bgr.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        straightened_bgr = cv2.warpAffine(
            original_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
    else:
        straightened_bgr = original_bgr

    # 4. Label region detection & crop
    cropped_bgr = detect_and_crop_label(straightened_bgr, deskewed_gray)

    # 5. Generate 8 preprocessing variants
    variants = generate_preprocessing_variants(cropped_bgr)
    enhanced_gray = variants["variant_a"]

    # 6. Save cropped image
    cropped_filename = f"inspection_{inspection_id}{suffix}_crop.png"
    cropped_path = os.path.join(storage_dir, cropped_filename)
    cv2.imwrite(cropped_path, cropped_bgr)

    return orig_filename, cropped_filename, enhanced_gray, variants
