"""
YOLO Text Region Detector
=========================
Detects text-dense bounding box regions on packaging labels before OCR.
This prevents small critical text (FSSAI, dates, MRP) from being dominated
by large product name text when running a full-image OCR pass.

Detection strategy (in order of availability):
  1. YOLOv8 custom model (if `models/yolo_label_detector.pt` exists)
  2. EasyOCR CRAFT-based text area detection (always available)
  3. OpenCV MSER region fallback (no external dependency)

Each detected region is tagged with a probable field type based on its
position and size on the label (top-center → product name, bottom-small → FSSAI/dates).
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Path where the trained YOLO model will be saved by yolo_trainer.py
_YOLO_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models", "yolo_label_detector.pt")
)

_yolo_model = None
_yolo_load_attempted = False


# ---------------------------------------------------------------------------
# Region type tagging
# ---------------------------------------------------------------------------

def _infer_region_type(x1: int, y1: int, x2: int, y2: int, img_h: int, img_w: int) -> str:
    """
    Heuristically infer what field type a bounding box likely contains
    based on its position and size relative to the full label.

    Rules (approximate, tuned for Indian packaging label layout conventions):
      - Top-center, large  → product_name
      - Bottom half, small → date_fssai (dates & FSSAI number typically bottom)
      - Center or right    → mrp_quantity
      - Anywhere, tall     → manufacturer_address
    """
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    box_w = x2 - x1
    box_h = y2 - y1
    area_frac = (box_w * box_h) / max(1, img_h * img_w)

    rel_cx = cx / img_w
    rel_cy = cy / img_h

    # Large block at top center → product name
    if rel_cy < 0.35 and rel_cx > 0.3 and rel_cx < 0.7 and area_frac > 0.04:
        return "product_name"

    # Small box in bottom 40% → likely dates / FSSAI
    if rel_cy > 0.60 and area_frac < 0.06:
        return "date_fssai"

    # Right-side, medium box → MRP
    if rel_cx > 0.65 and area_frac < 0.1:
        return "mrp_quantity"

    # Multi-line medium block → manufacturer / address
    if box_h > 2.5 * box_w and area_frac > 0.02:
        return "manufacturer"

    return "general_text"


# ---------------------------------------------------------------------------
# YOLO model loader (lazy, with graceful fallback)
# ---------------------------------------------------------------------------

def _try_load_yolo_model():
    """Attempt to load the custom-trained YOLOv8 model. Fails silently."""
    global _yolo_model, _yolo_load_attempted
    if _yolo_load_attempted:
        return _yolo_model
    _yolo_load_attempted = True

    if not os.path.exists(_YOLO_MODEL_PATH):
        logger.info(
            f"YOLOv8 label detector model not found at {_YOLO_MODEL_PATH}. "
            "Using CRAFT/MSER text detection instead. "
            "Run yolo_trainer.py to train the model."
        )
        return None

    try:
        from ultralytics import YOLO
        _yolo_model = YOLO(_YOLO_MODEL_PATH)
        logger.info(f"YOLOv8 label detector loaded from {_YOLO_MODEL_PATH}")
        return _yolo_model
    except Exception as e:
        logger.warning(f"Could not load YOLOv8 model: {e}. Falling back to CRAFT detection.")
        return None


# ---------------------------------------------------------------------------
# CRAFT-based detection (EasyOCR internal text area detector)
# ---------------------------------------------------------------------------

def _detect_via_craft(
    img_bgr: np.ndarray,
    min_confidence: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Use EasyOCR's CRAFT network to detect text bounding boxes WITHOUT
    performing character-level recognition. This is fast and accurate
    for locating where text exists on the label.

    Returns list of region dicts:
      {x1, y1, x2, y2, confidence, region_type, crop}
    """
    try:
        import easyocr

        # Re-use the singleton reader if it already exists
        from app.ocr.ocr_service import get_easyocr_reader
        reader = get_easyocr_reader()
        if reader is None:
            return []

        h, w = img_bgr.shape[:2]

        # Run detection-only pass (no character recognition)
        # EasyOCR returns bounding boxes with confidence when we call readtext
        # We use it at detection level by setting text_threshold high
        results = reader.readtext(
            img_bgr,
            decoder="greedy",
            beamWidth=5,
            contrast_ths=0.1,
            adjust_contrast=0.5,
            text_threshold=0.5,
            low_text=0.25,
            link_threshold=0.3,
            width_ths=0.5,
            height_ths=0.5,
            mag_ratio=1.5,
        )

        regions = []
        seen_boxes = []

        for bbox, text, conf in results:
            if conf < min_confidence:
                continue

            # bbox is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] (polygon)
            pts = np.array(bbox, dtype=np.int32)
            rx, ry, rw, rh = cv2.boundingRect(pts)

            # Clamp to image bounds
            rx = max(0, rx)
            ry = max(0, ry)
            rx2 = min(w, rx + rw)
            ry2 = min(h, ry + rh)

            if rw < 8 or rh < 6:
                continue

            # Skip near-duplicate boxes
            is_dup = False
            for (sx, sy, sx2, sy2) in seen_boxes:
                inter_x = max(0, min(rx2, sx2) - max(rx, sx))
                inter_y = max(0, min(ry2, sy2) - max(ry, sy))
                inter_area = inter_x * inter_y
                box_area = rw * rh
                if box_area > 0 and inter_area / box_area > 0.6:
                    is_dup = True
                    break

            if is_dup:
                continue

            seen_boxes.append((rx, ry, rx2, ry2))
            region_type = _infer_region_type(rx, ry, rx2, ry2, h, w)

            # Expand box by 3px padding for safer OCR crop
            pad = 4
            crop = img_bgr[
                max(0, ry - pad):min(h, ry2 + pad),
                max(0, rx - pad):min(w, rx2 + pad)
            ]

            regions.append({
                "x1": rx, "y1": ry, "x2": rx2, "y2": ry2,
                "confidence": round(float(conf), 3),
                "region_type": region_type,
                "text_hint": text.strip(),
                "crop": crop,
            })

        # Sort by y-position (top to bottom reading order)
        regions.sort(key=lambda r: r["y1"])
        return regions

    except Exception as e:
        logger.warning(f"CRAFT text detection failed: {e}")
        return []


# ---------------------------------------------------------------------------
# MSER-based region detection (pure OpenCV, always available)
# ---------------------------------------------------------------------------

def _detect_via_mser(img_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """
    Fallback text region detection using MSER.
    Clusters nearby text components into word/line bounding boxes.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    try:
        mser = cv2.MSER_create(
            _delta=5,
            _min_area=20,
            _max_area=int(h * w * 0.04),
            _max_variation=0.25,
        )
        regions, _ = mser.detectRegions(gray)
    except Exception:
        return []

    if not regions:
        return []

    raw_boxes = []
    for reg in regions:
        x, y, rw, rh = cv2.boundingRect(reg.reshape(-1, 1, 2))
        if rw < 8 or rh < 6:
            continue
        raw_boxes.append((x, y, x + rw, y + rh))

    # Group nearby boxes
    merged = _cluster_boxes(raw_boxes, gap_x=15, gap_y=8)

    result = []
    for (x1, y1, x2, y2) in merged:
        bw = x2 - x1
        bh = y2 - y1
        if bw < 15 or bh < 8:
            continue

        pad = 3
        crop = img_bgr[
            max(0, y1 - pad):min(h, y2 + pad),
            max(0, x1 - pad):min(w, x2 + pad)
        ]
        region_type = _infer_region_type(x1, y1, x2, y2, h, w)

        result.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "confidence": 0.5,
            "region_type": region_type,
            "text_hint": "",
            "crop": crop,
        })

    result.sort(key=lambda r: r["y1"])
    return result


def _cluster_boxes(
    boxes: List[Tuple[int, int, int, int]],
    gap_x: int = 15,
    gap_y: int = 8,
) -> List[Tuple[int, int, int, int]]:
    """Group bounding boxes that are close together into text-line clusters."""
    if not boxes:
        return []

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged = [boxes[0]]

    for x1, y1, x2, y2 in boxes[1:]:
        mx1, my1, mx2, my2 = merged[-1]

        x_overlap = x1 <= mx2 + gap_x and x2 >= mx1 - gap_x
        y_overlap = y1 <= my2 + gap_y and y2 >= my1 - gap_y

        if x_overlap and y_overlap:
            merged[-1] = (min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2))
        else:
            merged.append((x1, y1, x2, y2))

    return merged


# ---------------------------------------------------------------------------
# YOLOv8 model detection
# ---------------------------------------------------------------------------

def _detect_via_yolo(img_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """
    Use the custom-trained YOLOv8 model to detect label field zones.
    Returns empty list if model is unavailable.
    """
    model = _try_load_yolo_model()
    if model is None:
        return []

    h, w = img_bgr.shape[:2]
    result = []

    try:
        preds = model.predict(img_bgr, conf=0.25, iou=0.4, verbose=False)
        if not preds:
            return []

        boxes = preds[0].boxes
        if boxes is None:
            return []

        class_names = model.names  # {0: 'product_name', 1: 'date_fssai', ...}

        for box in boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = class_names.get(cls_id, "general_text")

            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            if x2 - x1 < 10 or y2 - y1 < 6:
                continue

            pad = 4
            crop = img_bgr[
                max(0, y1 - pad):min(h, y2 + pad),
                max(0, x1 - pad):min(w, x2 + pad)
            ]

            result.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "confidence": round(conf, 3),
                "region_type": cls_name,
                "text_hint": "",
                "crop": crop,
            })

        result.sort(key=lambda r: r["y1"])
    except Exception as e:
        logger.warning(f"YOLOv8 inference failed: {e}")
        return []

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_text_regions(
    img_bgr: np.ndarray,
    use_yolo: bool = True,
    min_regions: int = 2,
) -> List[Dict[str, Any]]:
    """
    Detect text bounding box regions on a label image.

    Priority:
      1. YOLOv8 custom model (if available and use_yolo=True)
      2. CRAFT (EasyOCR text area detection)
      3. MSER (pure OpenCV, always works)

    Args:
        img_bgr:      BGR label image (already cropped to label area)
        use_yolo:     Whether to attempt YOLOv8 detection first
        min_regions:  Minimum regions required; falls back to next method if fewer found

    Returns:
        List of region dicts with keys: x1, y1, x2, y2, confidence, region_type, crop
        Always includes the full image as the first region (region_type='full_image').
    """
    h, w = img_bgr.shape[:2]

    # Always include full image as baseline region
    full_region = {
        "x1": 0, "y1": 0, "x2": w, "y2": h,
        "confidence": 1.0,
        "region_type": "full_image",
        "text_hint": "",
        "crop": img_bgr.copy(),
    }

    regions = []

    # Try YOLO first
    if use_yolo:
        yolo_regions = _detect_via_yolo(img_bgr)
        if len(yolo_regions) >= min_regions:
            logger.debug(f"YOLOv8 detected {len(yolo_regions)} text regions")
            regions = yolo_regions

    # Fallback to CRAFT
    if len(regions) < min_regions:
        craft_regions = _detect_via_craft(img_bgr)
        if len(craft_regions) >= min_regions:
            logger.debug(f"CRAFT detected {len(craft_regions)} text regions")
            regions = craft_regions

    # Fallback to MSER
    if len(regions) < min_regions:
        mser_regions = _detect_via_mser(img_bgr)
        if len(mser_regions) >= min_regions:
            logger.debug(f"MSER detected {len(mser_regions)} text regions")
            regions = mser_regions

    if not regions:
        logger.debug("No sub-regions detected — using full image only")

    # Full image always first, followed by specific regions (capped to top 8 by confidence)
    top_regions = sorted(regions, key=lambda r: r["confidence"], reverse=True)[:8]
    # Re-sort by reading order
    top_regions.sort(key=lambda r: (r["y1"], r["x1"]))

    return [full_region] + top_regions


def get_field_specific_crops(
    regions: List[Dict[str, Any]],
    field: str,
) -> List[np.ndarray]:
    """
    Filter detected regions for a specific field type.
    Returns list of cropped numpy images for that field.

    Args:
        regions:  Output of detect_text_regions()
        field:    One of 'date_fssai', 'mrp_quantity', 'manufacturer', 'product_name', 'full_image'
    """
    return [
        r["crop"] for r in regions
        if r["region_type"] == field and r["crop"] is not None and r["crop"].size > 0
    ]
