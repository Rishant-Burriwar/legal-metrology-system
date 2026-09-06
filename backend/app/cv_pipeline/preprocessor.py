import os
import cv2
import numpy as np
from typing import Tuple, Optional


def deskew_image(gray_img: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detect skew angle and rotate image to straighten it."""
    # Invert and threshold to isolate dark text on light bg or vice-versa
    thresh = cv2.adaptiveThreshold(
        gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6
    )

    # Find non-zero points
    pts = np.column_stack(np.where(thresh > 0))
    if len(pts) < 100:
        return gray_img, 0.0

    rect = cv2.minAreaRect(pts)
    angle = rect[-1]

    # OpenCV minAreaRect returns angle in [-90, 0)
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Filter out excessive or near-zero rotation
    if abs(angle) < 0.5 or abs(angle) > 30.0:
        return gray_img, 0.0

    (h, w) = gray_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated, angle


def detect_and_crop_label(img: np.ndarray, gray: np.ndarray) -> np.ndarray:
    """Detect largest rectangular contour representing packaging label and crop."""
    h_img, w_img = img.shape[:2]
    total_area = h_img * w_img

    # Edge detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 40, 160)

    # Dilate edges to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edged, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img

    # Find largest rectangular-like contour
    best_crop = None
    max_area = 0

    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        area = cv2.contourArea(c)
        if area < 0.12 * total_area:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.03 * peri, True)

        # Look for 4 to 8 sided polygons (allowing rounded corners)
        if 4 <= len(approx) <= 8 and area > max_area:
            x, y, w, h = cv2.boundingRect(c)
            # Add safe margin around label
            pad_x = int(0.02 * w)
            pad_y = int(0.02 * h)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w_img, x + w + pad_x)
            y2 = min(h_img, y + h + pad_y)

            # Check if cropped area is reasonably proportioned
            if (x2 - x1) > 0.3 * w_img or (y2 - y1) > 0.3 * h_img:
                best_crop = img[y1:y2, x1:x2]
                max_area = area

    return best_crop if best_crop is not None else img


def process_label_image(
    image_bytes: bytes,
    storage_dir: str,
    inspection_id: int,
) -> Tuple[str, str, np.ndarray]:
    """
    Complete OpenCV preprocessing pipeline:
    1. Grayscale conversion
    2. Denoise (fastNlMeansDenoising)
    3. Deskew
    4. Contrast enhancement (CLAHE)
    5. Contour-based label region detection & crop
    6. Save original and cropped images to storage
    """
    os.makedirs(storage_dir, exist_ok=True)

    # Decode image from raw bytes
    np_arr = np.frombuffer(image_bytes, np.uint8)
    original_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if original_bgr is None:
        raise ValueError("Could not decode image from provided bytes.")

    # Save original image
    orig_filename = f"inspection_{inspection_id}_orig.png"
    orig_path = os.path.join(storage_dir, orig_filename)
    cv2.imwrite(orig_path, original_bgr)

    # 1. Grayscale
    gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Denoise
    # For large images, downscale slightly for denoising speed then apply
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 3. Deskew
    deskewed_gray, angle = deskew_image(denoised)

    # Deskew color image as well
    if abs(angle) > 0.5:
        (h, w) = original_bgr.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        straightened_bgr = cv2.warpAffine(
            original_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
    else:
        straightened_bgr = original_bgr

    # 4. Region Detection & Cropping
    cropped_bgr = detect_and_crop_label(straightened_bgr, deskewed_gray)

    # 5. Contrast Enhancement on cropped image for OCR
    cropped_gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(cropped_gray)

    # Save cropped image
    cropped_filename = f"inspection_{inspection_id}_crop.png"
    cropped_path = os.path.join(storage_dir, cropped_filename)
    cv2.imwrite(cropped_path, cropped_bgr)

    return orig_filename, cropped_filename, enhanced_gray
