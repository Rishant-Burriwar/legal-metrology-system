import os
import base64
import logging
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, status, HTTPException
from fastapi.responses import JSONResponse

from app.cv_pipeline.quality_assessor import assess_image_quality
from app.cv_pipeline.preprocessor import (
    process_label_image,
    conditional_denoise,
    deskew_image,
    detect_and_crop_label,
    generate_preprocessing_variants,
    auto_deblur,
    super_contrast_stretch,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preprocess", tags=["Image Preprocessing Lab"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "images"))


def _encode_image_to_base64(img: np.ndarray) -> str:
    """Encode a numpy image (grayscale or BGR) to base64 PNG string."""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        return ""
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


@router.post("/analyze")
async def analyze_preprocessing(
    image: UploadFile = File(...),
):
    """
    Image Preprocessing Lab endpoint.
    Takes a raw product label image and returns:
    - Quality assessment metrics
    - All intermediate preprocessing stages as base64 images
    - All 5 OCR-ready variants (A through E) as base64 images
    - Per-variant sharpness and contrast metrics
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image (PNG, JPEG, etc.).",
        )

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file received.",
        )

    # Decode image
    np_arr = np.frombuffer(image_bytes, np.uint8)
    original_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if original_bgr is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode image.",
        )

    # 1. Quality Assessment
    quality_result = assess_image_quality(original_bgr)

    # 2. Pipeline stages
    gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
    denoised = conditional_denoise(gray)
    deskewed, skew_angle = deskew_image(denoised)

    # Apply deskew to color image for cropping
    if abs(skew_angle) > 0.5:
        (h, w) = original_bgr.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), skew_angle, 1.0)
        straightened_bgr = cv2.warpAffine(
            original_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
    else:
        straightened_bgr = original_bgr

    cropped_bgr = detect_and_crop_label(straightened_bgr, deskewed)

    # 3. Auto-deblur
    cropped_gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    deblurred = auto_deblur(cropped_gray)

    # 4. Generate all 5 variants
    variants = generate_preprocessing_variants(cropped_bgr)

    # Compute per-variant metrics
    def compute_metrics(img):
        lap = float(cv2.Laplacian(img, cv2.CV_64F).var())
        contrast = float(np.std(img))
        brightness = float(np.mean(img))
        return {
            "sharpness": round(lap, 2),
            "contrast": round(contrast, 2),
            "brightness": round(brightness, 1),
        }

    # Build response with all stages and variants
    stages = {
        "original": {
            "image": _encode_image_to_base64(original_bgr),
            "label": "Original Upload",
            "description": "Raw uploaded image before any processing",
            "metrics": compute_metrics(gray),
        },
        "grayscale": {
            "image": _encode_image_to_base64(gray),
            "label": "Grayscale",
            "description": "Converted to single-channel grayscale",
            "metrics": compute_metrics(gray),
        },
        "denoised": {
            "image": _encode_image_to_base64(denoised),
            "label": "Noise-Aware Denoise",
            "description": "Conditional denoising — only applied if noise detected (preserves clean images)",
            "metrics": compute_metrics(denoised),
        },
        "deskewed": {
            "image": _encode_image_to_base64(deskewed),
            "label": f"Deskewed ({skew_angle:+.1f}°)",
            "description": f"Rotation corrected by {skew_angle:+.1f}° using minAreaRect estimation",
            "metrics": compute_metrics(deskewed),
        },
        "cropped": {
            "image": _encode_image_to_base64(cropped_bgr),
            "label": "Label Detected & Cropped",
            "description": "Contour-based label detection with perspective rectification and border trimming",
            "metrics": compute_metrics(cropped_gray),
        },
        "deblurred": {
            "image": _encode_image_to_base64(deblurred),
            "label": "Auto-Deblurred",
            "description": "Wiener deconvolution applied if blur detected (sharpness < 80)",
            "metrics": compute_metrics(deblurred),
        },
    }

    variant_info = {
        "variant_a": {
            "label": "Variant A — Balanced CLAHE",
            "description": "CLAHE (clipLimit=3.0, 4×4 tiles) + Unsharp Mask — best for standard labels",
        },
        "variant_b": {
            "label": "Variant B — Illumination Normalized",
            "description": "Division normalization + Bilateral filter + Morphological closing — best for shadows/glare",
        },
        "variant_c": {
            "label": "Variant C — 2× Upscaled",
            "description": "2.0× bicubic upscale + CLAHE + Sharpened — best for small text",
        },
        "variant_d": {
            "label": "Variant D — Adaptive Binary",
            "description": "Otsu/Adaptive threshold binarization — maximum text/background separation",
        },
        "variant_e": {
            "label": "Variant E — 2.5× Super-Res",
            "description": "2.5× upscale + Bilateral + CLAHE — best for micro-text on tiny labels",
        },
        "variant_f": {
            "label": "Variant F — Inverted Binary",
            "description": "Adaptive threshold + inversion — recovers light-on-dark embossed/debossed text",
        },
        "variant_g": {
            "label": "Variant G — Morphological Top-Hat",
            "description": "Top-hat transform + CLAHE — extracts bright text from uneven illumination backgrounds",
        },
        "variant_h": {
            "label": "Variant H — Super Contrast Stretch",
            "description": "Percentile contrast stretch + CLAHE — best for foil/metallic label surfaces",
        },
    }

    variant_results = {}
    for key, img in variants.items():
        info = variant_info.get(key, {"label": key, "description": ""})
        variant_results[key] = {
            "image": _encode_image_to_base64(img),
            "label": info["label"],
            "description": info["description"],
            "metrics": compute_metrics(img),
            "dimensions": f"{img.shape[1]}×{img.shape[0]}",
        }

    # Gemini AI packaging visual analysis if configured
    gemini_analysis = None
    try:
        from app.services.gemini_service import get_gemini_service
        g_svc = get_gemini_service()
        if g_svc.is_configured:
            gemini_analysis = g_svc.analyze_packaging_image(image_bytes)
    except Exception as e:
        logger.warning(f"ImageLab Gemini analysis skipped: {e}")

    return JSONResponse(content={
        "quality_assessment": quality_result,
        "gemini_analysis": gemini_analysis,
        "stages": stages,
        "variants": variant_results,
        "pipeline_summary": {
            "skew_angle": round(skew_angle, 2),
            "original_dimensions": f"{original_bgr.shape[1]}×{original_bgr.shape[0]}",
            "cropped_dimensions": f"{cropped_bgr.shape[1]}×{cropped_bgr.shape[0]}",
            "quality_acceptable": quality_result["is_acceptable"],
            "quality_score": quality_result["quality_score"],
        },
    })


@router.post("/gemini-analyze")
async def analyze_with_gemini(
    image: UploadFile = File(...),
    is_food_product: bool = True,
):
    """
    Dedicated Gemini Multimodal AI packaging diagnosis & extraction endpoint for ImageLab.
    Returns visual packaging quality audit, surface reflections/glare, and statutory extractions.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image received.",
        )

    from app.services.gemini_service import get_gemini_service
    g_svc = get_gemini_service()

    if not g_svc.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini AI is not configured or API key is missing.",
        )

    try:
        visual_analysis = g_svc.analyze_packaging_image(image_bytes)
        extraction = g_svc.extract_statutory_fields(image_bytes, is_food_product=is_food_product)

        return {
            "visual_analysis": visual_analysis,
            "extraction": extraction,
            "engine": "Gemini Multimodal AI",
        }
    except Exception as e:
        logger.error(f"Gemini analyze endpoint failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini visual analysis failed: {str(e)}",
        )

