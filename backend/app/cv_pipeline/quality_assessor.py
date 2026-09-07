import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from app.core.config import settings

# 7 Practical Re-upload Tips for Users
PRACTICAL_REUPLOAD_TIPS = [
    "Lighting: Ensure even, diffused lighting across the entire label. Avoid direct flash or heavy shadows.",
    "Glare & Reflections: Tilt the package slightly or change angle if glossy plastic/foil causes white glare patches.",
    "Framing & Distance: Fill 70-80% of the frame with the label text, keeping all margins visible without cropping.",
    "Angle & Alignment: Hold your camera directly parallel to the label surface to eliminate perspective tilt.",
    "Sharpness & Focus: Tap your phone screen on small text to lock focus before snapping. Hold steady.",
    "Resolution & Cleanliness: Wipe your camera lens clean and upload at least 800x600 px (avoid thumbnail compression).",
    "Flat Packaging: If inspecting a flexible pouch or bag, flatten the printed panel so text isn't warped over creases."
]


def compute_laplacian_variance(gray: np.ndarray) -> float:
    """Compute variance of Laplacian (standard objective sharpness metric)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def compute_tenengrad(gray: np.ndarray) -> float:
    """Compute Tenengrad gradient magnitude score for secondary sharpness confirmation."""
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(gx**2 + gy**2)
    return float(np.mean(gradient_magnitude))


def compute_noise_level(gray: np.ndarray) -> float:
    """Estimate image noise standard deviation via high-pass residual."""
    blurred = cv2.medianBlur(gray, 3)
    diff = cv2.absdiff(gray, blurred)
    return float(np.std(diff))


def compute_jpeg_blocking_metric(gray: np.ndarray) -> float:
    """
    Estimate compression artifacts by analyzing 8x8 block boundary discontinuities.
    Returns normalized artifact score (0.0 = clean, > 1.0 = heavy blockiness).
    """
    h, w = gray.shape[:2]
    if h < 16 or w < 16:
        return 0.0

    r1 = gray[7:-1:8, :].astype(np.float32)
    r2 = gray[8::8, :].astype(np.float32)
    min_r = min(r1.shape[0], r2.shape[0])
    diff_y = np.abs(r1[:min_r, :] - r2[:min_r, :]) if min_r > 0 else np.array([0.0])

    c1 = gray[:, 7:-1:8].astype(np.float32)
    c2 = gray[:, 8::8].astype(np.float32)
    min_c = min(c1.shape[1], c2.shape[1])
    diff_x = np.abs(c1[:, :min_c] - c2[:, :min_c]) if min_c > 0 else np.array([0.0])

    boundary_diff = (float(np.mean(diff_y)) + float(np.mean(diff_x))) / 2.0
    return round(boundary_diff, 2)


def estimate_skew(gray: np.ndarray) -> float:
    """Estimate principal text skew angle in degrees."""
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6
    )
    pts = np.column_stack(np.where(thresh > 0))
    if len(pts) < 100:
        return 0.0

    rect = cv2.minAreaRect(pts)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    return float(angle)


def assess_image_quality(
    image: np.ndarray,
    custom_blur_thresh: float = None,
) -> Dict[str, Any]:
    """
    Mandatory pre-OCR image quality validation gate.
    Evaluates:
      - Sharpness (Laplacian variance & Tenengrad)
      - Resolution (Width & Height)
      - Brightness (Underexposure & Overexposure/Glare)
      - Contrast (Standard deviation)
      - Noise level
      - Skew angle
      - Text visibility / Edge density
      - Compression artifacts

    Returns a structured dictionary with:
      - is_acceptable: bool (False -> DO NOT RUN OCR)
      - quality_score: float (0 - 100)
      - metrics: Dict of raw numbers
      - rejection_reasons: List[str]
      - recommendations: List[str]
    """
    blur_thresh = custom_blur_thresh or settings.BLUR_THRESHOLD

    if image is None or image.size == 0:
        return {
            "is_acceptable": False,
            "quality_score": 0.0,
            "metrics": {},
            "rejection_reasons": ["Invalid or empty image data received."],
            "recommendations": PRACTICAL_REUPLOAD_TIPS,
        }

    # Grayscale conversion
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w, c = image.shape
    else:
        gray = image
        h, w = image.shape

    rejection_reasons = []

    # 1. Resolution Check
    if w < settings.MIN_IMAGE_WIDTH or h < settings.MIN_IMAGE_HEIGHT:
        rejection_reasons.append(
            f"The image resolution is too low ({w}x{h} px). "
            f"Minimum required is {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT} px. "
            "Please upload a higher-resolution photo."
        )

    # 2. Sharpness / Blur Check
    lap_var = compute_laplacian_variance(gray)
    tenengrad = compute_tenengrad(gray)

    if lap_var < blur_thresh:
        rejection_reasons.append(
            "The image is too blurry to extract text accurately. "
            "Please upload a clearer, higher-resolution image."
        )

    # 3. Brightness & Exposure Check
    mean_brightness = float(np.mean(gray))
    if mean_brightness < settings.MIN_BRIGHTNESS:
        rejection_reasons.append(
            f"The image is too dark (brightness {mean_brightness:.1f}/255). "
            "Please ensure good lighting without harsh shadows."
        )
    elif mean_brightness > settings.MAX_BRIGHTNESS:
        rejection_reasons.append(
            f"The image is overexposed or washed out with harsh glare (brightness {mean_brightness:.1f}/255). "
            "Please retake avoiding direct flash or specular reflections."
        )

    # 4. Contrast Check (computed before glare check which depends on it)
    contrast_std = float(np.std(gray))
    if contrast_std < settings.MIN_CONTRAST:
        rejection_reasons.append(
            f"The image has very low contrast (contrast std {contrast_std:.1f}). "
            "Text cannot be differentiated from the background. Please ensure adequate contrast."
        )

    # 5. Glare clipping check (depends on contrast_std)
    glare_fraction = float(np.sum(gray > 252)) / float(gray.size)
    if glare_fraction > 0.92 and contrast_std < 25.0:
        rejection_reasons.append(
            "Severe glare/overexposure detected across the label surface causing text washout."
        )

    # 6. Noise Check
    noise_std = compute_noise_level(gray)
    if noise_std > settings.MAX_NOISE_STD:
        rejection_reasons.append(
            f"Excessive sensor noise detected ({noise_std:.1f}). "
            "Please capture in brighter lighting to reduce digital noise."
        )

    # 7. Skew Estimation
    skew_deg = estimate_skew(gray)
    if abs(skew_deg) > settings.MAX_SKEW_ANGLE:
        rejection_reasons.append(
            f"Severe package tilt/rotation detected ({skew_deg:+.1f}°). "
            "Please align the package straight before capturing."
        )

    # 8. Text Visibility / Edge Density
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.sum(edges > 0)) / float(edges.size)
    if edge_density < 0.005 and lap_var < (blur_thresh * 1.5):
        rejection_reasons.append(
            "No discernible text or high-frequency edge details found in image."
        )

    # 9. Compression Artifacts
    blockiness = compute_jpeg_blocking_metric(gray)

    # Compute composite Quality Score (0 to 100)
    # Weights: Sharpness (35%), Contrast (25%), Brightness balance (20%), Noise/Resolution (20%)
    sharp_factor = min(1.0, lap_var / 300.0)
    contrast_factor = min(1.0, contrast_std / 60.0)
    bright_factor = 1.0 - (abs(mean_brightness - 128.0) / 128.0)
    res_factor = min(1.0, (w * h) / (1200.0 * 900.0))

    composite_score = round(
        (sharp_factor * 35.0) + (contrast_factor * 25.0) + (bright_factor * 20.0) + (res_factor * 20.0),
        1
    )
    # Clip between 0 and 100
    composite_score = max(0.0, min(100.0, composite_score))

    is_acceptable = len(rejection_reasons) == 0

    metrics = {
        "sharpness_laplacian": round(lap_var, 2),
        "sharpness_tenengrad": round(tenengrad, 2),
        "blur_threshold": blur_thresh,
        "width": w,
        "height": h,
        "mean_brightness": round(mean_brightness, 1),
        "contrast_std": round(contrast_std, 1),
        "noise_std": round(noise_std, 1),
        "skew_degrees": round(skew_deg, 1),
        "edge_density": round(edge_density, 4),
        "compression_blockiness": round(blockiness, 2),
    }

    return {
        "is_acceptable": is_acceptable,
        "quality_score": composite_score,
        "metrics": metrics,
        "rejection_reasons": rejection_reasons,
        "recommendations": PRACTICAL_REUPLOAD_TIPS if not is_acceptable else [],
    }
