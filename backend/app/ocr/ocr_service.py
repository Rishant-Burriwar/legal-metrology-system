"""
Adaptive OCR Pipeline — Legal Metrology Label Inspector
=======================================================

Key improvements over previous version:
  1. YOLO/CRAFT text region detection → OCR runs on sub-regions, not just full image.
     FSSAI numbers and dates in small print are no longer dominated by product name text.
  2. Field-aware consensus scoring — blocks are scored by whether they contain
     recognizable legal metrology patterns (date, FSSAI 14-digit, MRP, etc.).
     A short accurate FSSAI number beats a long garbage text string.
  3. 8 preprocessing variants (A–H) — all used in the pipeline.
  4. Better EasyOCR parameters tuned for dense packaging text.
  5. Multi-PSM Tesseract fallback (PSM 6, 7, 4, 11).
"""

import logging
import re
from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import cv2
from app.core.config import settings
from app.extraction.disambiguation import disambiguate_text_string

logger = logging.getLogger(__name__)

_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader (CPU mode)...")
            _easyocr_reader = easyocr.Reader(
                ["en"],
                gpu=False,
                model_storage_directory=None,
                download_enabled=True,
                verbose=False,
            )
            logger.info("EasyOCR reader initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            _easyocr_reader = None
    return _easyocr_reader


# ---------------------------------------------------------------------------
# Tesseract fallback
# ---------------------------------------------------------------------------

def try_tesseract(image: np.ndarray, psm: int = 6) -> Tuple[str, float]:
    """
    Tesseract fallback with configurable PSM mode.
    PSM modes used:
      6  = Assume single uniform block of text (default)
      7  = Treat the image as a single text line
      4  = Single column of text, variable sizes
      11 = Sparse text — find as much text as possible
    """
    try:
        import pytesseract

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # For PSM 7 (single line), skip Otsu and use direct grayscale
        if psm == 7:
            binary = gray
        else:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        config = f"--psm {psm} --oem 3"
        text = pytesseract.image_to_string(binary, config=config)

        try:
            data = pytesseract.image_to_data(binary, config=config, output_type=pytesseract.Output.DICT)
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.5
        except Exception:
            avg_conf = 0.5

        return text.strip(), avg_conf
    except Exception as e:
        logger.warning(f"pytesseract fallback (PSM {psm}) failed: {e}")
        return "", 0.0


# ---------------------------------------------------------------------------
# Field-aware pattern scoring
# ---------------------------------------------------------------------------

# Patterns for legal metrology fields — if a block matches, it gets a confidence boost
_FIELD_PATTERNS: List[Tuple[str, float, re.Pattern]] = [
    # (field_name, boost_factor, compiled_regex)
    ("fssai",       0.25, re.compile(r"\b\d{14}\b")),
    ("fssai_tag",   0.20, re.compile(r"fssai|lic\s*no", re.IGNORECASE)),
    ("date",        0.20, re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s/\-\.]\d{2,4}\b|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b", re.IGNORECASE)),
    ("mfg_date",    0.20, re.compile(r"\b(?:mfg|mfd|manufactured|packed|pkd)[\s\.\:]*(?:date|dt)?[\s\.\:]*\d", re.IGNORECASE)),
    ("expiry",      0.20, re.compile(r"\b(?:exp|expiry|best\s*before|use\s*by|bb)[\s\.\:]+", re.IGNORECASE)),
    ("mrp",         0.20, re.compile(r"\b(?:mrp|m\.r\.p\.?|max\s*retail\s*price)[\s\.\:₹Rs]*\d", re.IGNORECASE)),
    ("price",       0.15, re.compile(r"[₹Rs]\s*\d+(?:\.\d{2})?|\bRs\.?\s*\d+")),
    ("net_qty",     0.15, re.compile(r"\b\d+\s*(?:g|gm|gms|kg|ml|l|ltr|pieces|pcs)\b", re.IGNORECASE)),
    ("mfr_by",      0.15, re.compile(r"\b(?:manufactured|marketed|packed|imported)\s+by\b", re.IGNORECASE)),
    ("incl_tax",    0.10, re.compile(r"incl(?:usive)?\s*(?:of\s*)?all\s*taxes", re.IGNORECASE)),
    ("country",     0.10, re.compile(r"(?:country\s*of\s*origin|made\s*in)\s*:?\s*\w+", re.IGNORECASE)),
    ("india",       0.05, re.compile(r"\bIndia\b|\bBharat\b", re.IGNORECASE)),
]


def score_block_by_field_patterns(text: str) -> float:
    """
    Score an OCR text block based on how many legal metrology field patterns it matches.
    Returns a cumulative bonus score in [0, 1].
    """
    if not text or len(text.strip()) < 3:
        return 0.0

    total_boost = 0.0
    for _, boost, pattern in _FIELD_PATTERNS:
        if pattern.search(text):
            total_boost += boost

    return min(total_boost, 1.0)


# ---------------------------------------------------------------------------
# Single OCR pass
# ---------------------------------------------------------------------------

def run_single_ocr_pass(
    image: np.ndarray,
    pass_name: str = "pass_1",
    region_type: str = "full_image",
) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Execute a single OCR pass on the given image.
    Uses EasyOCR with parameters tuned for dense packaging labels.
    Falls back to multi-PSM Tesseract if EasyOCR returns little/low-confidence text.

    Args:
        image:       Preprocessed grayscale or BGR image
        pass_name:   Label for logging & block attribution
        region_type: Type of region being processed (from YOLO/CRAFT detection)

    Returns:
        (raw_text, avg_confidence, block_list)
    """
    reader = get_easyocr_reader()
    raw_text = ""
    avg_conf = 0.0
    blocks: List[Dict[str, Any]] = []

    if reader is not None:
        try:
            # Parameters tuned for Indian packaging text:
            # - mag_ratio=2.0: enlarges small text before detection
            # - min_size=5: catches very small license number text
            # - contrast_ths=0.05: picks up low-contrast embossed text
            # - width_ths=0.8, height_ths=0.8: allows wider character grouping
            results = reader.readtext(
                image,
                decoder="beamsearch",
                beamWidth=10,
                contrast_ths=0.05,
                adjust_contrast=0.7,
                text_threshold=0.55,
                low_text=0.3,
                link_threshold=0.3,
                width_ths=0.8,
                height_ths=0.8,
                mag_ratio=2.0,
                min_size=5,
            )
            text_lines = []
            confs = []

            for bbox, text, conf in results:
                clean_text = text.strip()
                if not clean_text:
                    continue

                # Field-aware confidence boosting
                field_bonus = score_block_by_field_patterns(clean_text)
                adjusted_conf = min(1.0, float(conf) + field_bonus * 0.3)

                text_lines.append(clean_text)
                confs.append(adjusted_conf)
                blocks.append({
                    "text": clean_text,
                    "confidence": round(adjusted_conf, 3),
                    "raw_confidence": round(float(conf), 3),
                    "field_bonus": round(field_bonus, 3),
                    "box": [[int(p[0]), int(p[1])] for p in bbox],
                    "source_pass": pass_name,
                    "region_type": region_type,
                })

            if text_lines:
                raw_text = "\n".join(text_lines)
                avg_conf = sum(confs) / len(confs) if confs else 0.0

        except Exception as e:
            logger.error(f"EasyOCR run error in {pass_name}: {e}")

    # Multi-PSM Tesseract fallback
    if len(raw_text.strip()) < 15 or avg_conf < 0.30:
        # Pick PSM based on region type
        if region_type in ("date_fssai",):
            psm_order = [7, 6, 11]  # Single line first for dates/FSSAI
        elif region_type in ("mrp_quantity",):
            psm_order = [7, 6]
        else:
            psm_order = [6, 4, 11]

        best_tess_text = ""
        best_tess_conf = 0.0
        best_psm = psm_order[0]

        for psm in psm_order:
            t_text, t_conf = try_tesseract(image, psm=psm)
            if len(t_text) > len(best_tess_text) or (len(t_text) == len(best_tess_text) and t_conf > best_tess_conf):
                # Prefer result with more field pattern matches when length is similar
                old_score = score_block_by_field_patterns(best_tess_text)
                new_score = score_block_by_field_patterns(t_text)
                if new_score >= old_score:
                    best_tess_text = t_text
                    best_tess_conf = t_conf
                    best_psm = psm

        if best_tess_text and len(best_tess_text) > len(raw_text):
            raw_text = best_tess_text
            avg_conf = max(avg_conf, best_tess_conf)
            blocks.append({
                "text": best_tess_text,
                "confidence": round(best_tess_conf, 3),
                "raw_confidence": round(best_tess_conf, 3),
                "field_bonus": round(score_block_by_field_patterns(best_tess_text), 3),
                "box": [],
                "source_pass": f"{pass_name}_tesseract_psm{best_psm}",
                "region_type": region_type,
            })

    return raw_text, round(avg_conf, 3), blocks


# ---------------------------------------------------------------------------
# OCR on YOLO/CRAFT detected sub-regions
# ---------------------------------------------------------------------------

def run_region_aware_ocr(
    cropped_bgr: np.ndarray,
    variants: Dict[str, np.ndarray],
) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Detect text regions on the label, then run OCR independently on each region.
    Region crops are processed with their own best variants.

    This avoids large product-name text dominating small FSSAI/date text.

    Returns: (combined_text, avg_confidence, all_blocks)
    """
    try:
        from app.cv_pipeline.yolo_detector import detect_text_regions
        regions = detect_text_regions(cropped_bgr, use_yolo=True, min_regions=2)
    except Exception as e:
        logger.warning(f"Region detection failed, using full-image only: {e}")
        regions = []

    # Always have at least the full image region
    if not regions:
        return "", 0.0, []

    all_blocks: List[Dict[str, Any]] = []
    all_texts: List[str] = []
    all_confs: List[float] = []

    # Select best variant per region type
    variant_priority = {
        "full_image":    ["variant_a", "variant_b", "variant_d"],
        "product_name":  ["variant_a", "variant_c"],
        "date_fssai":    ["variant_c", "variant_e", "variant_d", "variant_g"],
        "mrp_quantity":  ["variant_a", "variant_d", "variant_h"],
        "manufacturer":  ["variant_b", "variant_a", "variant_f"],
        "general_text":  ["variant_a", "variant_b", "variant_d"],
    }

    seen_text_norms = set()

    for region in regions:
        rtype = region.get("region_type", "general_text")
        crop = region.get("crop")

        if crop is None or crop.size == 0:
            continue

        # For small crops, apply CLAHE enhancement before OCR
        if len(crop.shape) == 3:
            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            crop_gray = crop

        if crop_gray.shape[0] < 15 or crop_gray.shape[1] < 15:
            continue

        # Upscale very small regions to at least 48px height for better OCR
        min_height = 48
        if crop_gray.shape[0] < min_height:
            scale = min_height / crop_gray.shape[0]
            crop_gray = cv2.resize(
                crop_gray,
                (int(crop_gray.shape[1] * scale), min_height),
                interpolation=cv2.INTER_CUBIC
            )
            crop = cv2.resize(
                crop,
                (int(crop.shape[1] * scale), min_height),
                interpolation=cv2.INTER_CUBIC
            ) if len(crop.shape) == 3 else crop_gray

        # Enhance the crop with CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        crop_enhanced = clahe.apply(crop_gray)

        pass_name = f"region_{rtype}"
        text, conf, r_blocks = run_single_ocr_pass(crop_enhanced, pass_name=pass_name, region_type=rtype)

        if not text.strip():
            continue

        # Deduplicate lines already seen
        new_lines = []
        for line in text.splitlines():
            norm = line.strip().lower()
            if norm and norm not in seen_text_norms and len(norm) > 2:
                seen_text_norms.add(norm)
                new_lines.append(line.strip())

        if new_lines:
            all_texts.extend(new_lines)
            all_confs.append(conf)
            all_blocks.extend(r_blocks)

    combined_text = "\n".join(all_texts)
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0

    return combined_text, round(avg_conf, 3), all_blocks


# ---------------------------------------------------------------------------
# Levenshtein similarity
# ---------------------------------------------------------------------------

def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity between two strings (0.0 – 1.0)."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    max_len = max(len1, len2)

    if len1 > 500 or len2 > 500:
        common = set(s1.lower().split()) & set(s2.lower().split())
        all_words = set(s1.lower().split()) | set(s2.lower().split())
        return len(common) / max(1, len(all_words))

    prev = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr = [i] + [0] * len2
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr

    return 1.0 - (prev[len2] / max_len)


# ---------------------------------------------------------------------------
# Consensus merge (field-aware)
# ---------------------------------------------------------------------------

def merge_ocr_consensus(
    pass_results: List[Tuple[str, float, List[Dict[str, Any]]]]
) -> Tuple[str, str, float, List[Dict[str, Any]]]:
    """
    Field-aware consensus fusion across multiple OCR passes.

    Strategy:
      1. Score each pass by BOTH text length AND field pattern density.
         A pass with a short FSSAI number and no garbage beats a pass with
         long garbage text and no patterns.
      2. Select the best pass as base text.
      3. Cross-validate with Levenshtein similarity.
      4. Merge unique lines from secondary passes if similarity is low.
      5. Boost confidence for blocks that appear across multiple passes.

    Returns: (raw_ocr_text, validated_ocr_text, final_confidence, all_blocks)
    """
    if not pass_results:
        return "", "", 0.0, []

    def pass_score(result: Tuple[str, float, List[Dict[str, Any]]]) -> float:
        text, conf, blocks = result
        text_len = len(text.strip())
        if text_len == 0:
            return 0.0

        # Field pattern density score
        field_density = score_block_by_field_patterns(text)

        # Block-level confidence average
        block_conf = (
            sum(b.get("confidence", 0) for b in blocks) / len(blocks)
            if blocks else conf
        )

        # Composite: length matters, but field patterns boost heavily
        return (text_len * 0.3) + (field_density * 40.0) + (block_conf * 15.0) + (conf * 10.0)

    sorted_passes = sorted(pass_results, key=pass_score, reverse=True)
    best_raw, best_conf, best_blocks = sorted_passes[0]

    if len(sorted_passes) > 1:
        secondary_raw = sorted_passes[1][0]
        similarity = _levenshtein_similarity(
            best_raw.lower().strip(),
            secondary_raw.lower().strip()
        )

        if similarity > 0.7:
            best_conf = min(1.0, best_conf + 0.1)
        elif similarity < 0.3 and len(secondary_raw.strip()) > 10:
            existing_lines = set(
                line.strip().lower() for line in best_raw.splitlines() if line.strip()
            )
            for line in secondary_raw.splitlines():
                stripped = line.strip()
                norm = stripped.lower()
                if stripped and norm not in existing_lines:
                    # Only merge if the line has field pattern content
                    if score_block_by_field_patterns(stripped) > 0.05 or len(existing_lines) < 5:
                        best_raw += "\n" + stripped
                        existing_lines.add(norm)

    # Aggregate unique blocks from all passes
    all_blocks: List[Dict[str, Any]] = []
    seen_texts: set = set()

    for _, _, blocks in sorted_passes:
        for b in blocks:
            norm = b["text"].strip().lower()
            if norm and norm not in seen_texts:
                seen_texts.add(norm)
                all_blocks.append(b)

    # Cross-pass confidence boosting
    block_text_counts: Dict[str, int] = {}
    for _, _, blocks in sorted_passes:
        for b in blocks:
            norm = b["text"].strip().lower()
            block_text_counts[norm] = block_text_counts.get(norm, 0) + 1

    for block in all_blocks:
        norm = block["text"].strip().lower()
        count = block_text_counts.get(norm, 0)
        if count > 1:
            block["confidence"] = min(1.0, block["confidence"] + 0.05 * (count - 1))
            block["cross_validated"] = True

    # Final confidence as weighted average of block confidences
    if all_blocks:
        final_conf = sum(b["confidence"] for b in all_blocks) / len(all_blocks)
    else:
        final_conf = best_conf

    raw_ocr_text = best_raw
    validated_ocr_text = disambiguate_text_string(best_raw)

    return raw_ocr_text, validated_ocr_text, round(final_conf, 3), all_blocks


# ---------------------------------------------------------------------------
# Main adaptive pipeline
# ---------------------------------------------------------------------------

def perform_adaptive_ocr_pipeline(
    variants: Dict[str, np.ndarray],
    cropped_bgr: Optional[np.ndarray] = None,
    max_retries: int = None,
) -> Dict[str, Any]:
    """
    Multi-stage adaptive retry OCR pipeline with 8 variants + region-aware OCR.

    Stage 0: Region-aware OCR (YOLO/CRAFT region detection + per-region OCR)
    Stage 1: Variant A (primary balanced)
    Stage 2: Variant B (illumination) + D (binary) — if stage 1 confidence low
    Stage 3: Variant C (2×) + E (2.5×) — if still low
    Stage 4: Variant F (inverted) + G (top-hat) + H (super-contrast) — worst-case

    Final: Consensus fusion across ALL passes.

    Args:
        variants:    Dict of 8 preprocessed variants from generate_preprocessing_variants()
        cropped_bgr: Original cropped BGR image for YOLO region detection (optional but recommended)
        max_retries: Override for settings.MAX_OCR_RETRIES
    """
    retries_limit = max_retries or settings.MAX_OCR_RETRIES
    pass_results: List[Tuple[str, float, List[Dict[str, Any]]]] = []
    retry_count = 0

    # --- Stage 0: Region-aware OCR (YOLO/CRAFT sub-region detection) ---
    if cropped_bgr is not None:
        try:
            region_text, region_conf, region_blocks = run_region_aware_ocr(cropped_bgr, variants)
            if region_text.strip():
                logger.info(f"Region-aware OCR: {len(region_blocks)} blocks, conf={region_conf:.3f}")
                pass_results.append((region_text, region_conf, region_blocks))
        except Exception as e:
            logger.warning(f"Region-aware OCR stage failed: {e}")

    # --- Stage 1: Variant A (primary balanced pass) ---
    var_a = variants.get("variant_a")
    if var_a is not None:
        text_a, conf_a, blocks_a = run_single_ocr_pass(var_a, pass_name="variant_a")
        pass_results.append((text_a, conf_a, blocks_a))
    else:
        conf_a = 0.0
        text_a = ""

    # Determine if we need further stages
    best_conf_so_far = max((r[1] for r in pass_results), default=0.0)
    best_len_so_far = max((len(r[0].strip()) for r in pass_results), default=0)

    # --- Stage 2: Variant B + D ---
    if retry_count < retries_limit and (best_conf_so_far < settings.CONFIDENCE_HIGH or best_len_so_far < 50):
        for var_key, var_name in [("variant_b", "Illumination Normalized"), ("variant_d", "Adaptive Binary")]:
            if retry_count >= retries_limit:
                break
            img = variants.get(var_key)
            if img is not None:
                logger.info(f"Stage 2: {var_name}...")
                t, c, b = run_single_ocr_pass(img, pass_name=var_key)
                pass_results.append((t, c, b))
                retry_count += 1

        best_conf_so_far = max((r[1] for r in pass_results), default=0.0)
        best_len_so_far = max((len(r[0].strip()) for r in pass_results), default=0)

    # --- Stage 3: Variant C + E ---
    if retry_count < retries_limit and (best_conf_so_far < settings.CONFIDENCE_MEDIUM or best_len_so_far < 60):
        for var_key, var_name in [("variant_c", "2× Upscaled"), ("variant_e", "2.5× Super-res")]:
            if retry_count >= retries_limit:
                break
            img = variants.get(var_key)
            if img is not None:
                logger.info(f"Stage 3: {var_name}...")
                t, c, b = run_single_ocr_pass(img, pass_name=var_key)
                pass_results.append((t, c, b))
                retry_count += 1

        best_conf_so_far = max((r[1] for r in pass_results), default=0.0)
        best_len_so_far = max((len(r[0].strip()) for r in pass_results), default=0)

    # --- Stage 4: Variant F + G + H (worst-case: dark/embossed/foil labels) ---
    if retry_count < retries_limit and (best_conf_so_far < settings.CONFIDENCE_MEDIUM or best_len_so_far < 40):
        for var_key, var_name in [
            ("variant_f", "Inverted Binary"),
            ("variant_g", "Top-Hat Transform"),
            ("variant_h", "Super Contrast"),
        ]:
            if retry_count >= retries_limit:
                break
            img = variants.get(var_key)
            if img is not None:
                logger.info(f"Stage 4: {var_name}...")
                t, c, b = run_single_ocr_pass(img, pass_name=var_key)
                pass_results.append((t, c, b))
                retry_count += 1

    # --- Consensus fusion ---
    raw_ocr_text, validated_ocr_text, final_conf, blocks = merge_ocr_consensus(pass_results)

    logger.info(
        f"OCR complete — passes={len(pass_results)}, retries={retry_count}, "
        f"conf={final_conf:.3f}, text_len={len(raw_ocr_text)}"
    )

    return {
        "raw_ocr_text": raw_ocr_text,
        "validated_ocr_text": validated_ocr_text,
        "ocr_confidence": round(final_conf, 3),
        "ocr_retry_count": retry_count,
        "blocks": blocks,
        "passes_executed": len(pass_results),
    }


def perform_ocr(image: np.ndarray) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Backward-compatible single-image OCR entrypoint.
    Returns (raw_ocr_text, average_confidence, block_details).
    """
    raw_text, conf, blocks = run_single_ocr_pass(image, pass_name="standard")
    return raw_text, conf, blocks
