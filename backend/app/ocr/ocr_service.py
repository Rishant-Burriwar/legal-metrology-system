import logging
from typing import Tuple, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            # Initialize reader with English; gpu=False safe for all machines
            logger.info("Initializing EasyOCR reader (CPU mode)...")
            _easyocr_reader = easyocr.Reader(["en"], gpu=False)
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            _easyocr_reader = None
    return _easyocr_reader


def try_tesseract(image: np.ndarray) -> str:
    """Fallback OCR using pytesseract if available."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.warning(f"pytesseract fallback unavailable or failed: {e}")
        return ""


def perform_ocr(image: np.ndarray) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Run EasyOCR on cropped image, falling back to pytesseract if needed.
    Returns:
        (raw_ocr_text, average_confidence, block_details)
    """
    reader = get_easyocr_reader()
    raw_text = ""
    avg_conf = 0.0
    blocks: List[Dict[str, Any]] = []

    if reader is not None:
        try:
            results = reader.readtext(image)
            text_lines = []
            confs = []

            for bbox, text, conf in results:
                clean_text = text.strip()
                if clean_text:
                    text_lines.append(clean_text)
                    confs.append(float(conf))
                    blocks.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "box": [[int(p[0]), int(p[1])] for p in bbox],
                    })

            if text_lines:
                raw_text = "\n".join(text_lines)
                avg_conf = sum(confs) / len(confs) if confs else 0.0
        except Exception as e:
            logger.error(f"EasyOCR run error: {e}")

    # Check if fallback to pytesseract is required
    if len(raw_text.strip()) < 15 or avg_conf < 0.25:
        logger.info("EasyOCR yielded low confidence or empty text. Attempting pytesseract fallback...")
        tess_text = try_tesseract(image)
        if tess_text:
            if len(tess_text) > len(raw_text):
                raw_text = tess_text
                avg_conf = max(avg_conf, 0.6)  # Default moderate confidence for tesseract

    return raw_text, round(avg_conf, 3), blocks
