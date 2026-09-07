import os
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, seed_database, SessionLocal
from app.models.models import Inspection
from app.cv_pipeline.quality_assessor import (
    assess_image_quality,
    compute_laplacian_variance,
    PRACTICAL_REUPLOAD_TIPS,
)
from app.cv_pipeline.preprocessor import (
    generate_preprocessing_variants,
    unsharp_mask,
    normalize_illumination,
    auto_deblur,
    conditional_denoise,
    trim_blank_borders,
)
from app.extraction.disambiguation import (
    disambiguate_numeric_string,
    disambiguate_text_string,
    validate_and_disambiguate_fssai,
    validate_and_disambiguate_net_quantity,
    validate_and_disambiguate_mrp,
    validate_and_disambiguate_date,
    fix_unit_ocr_errors,
    normalize_unit,
    UNCERTAIN_TAG,
)
from app.extraction.extractor import extract_compliance_fields
from app.rule_engine.rules import evaluate_compliance
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline, _levenshtein_similarity

client = TestClient(app)
SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_images"))


@pytest.fixture(scope="module")
def auth_header():
    res = client.post("/auth/login", json={"email": "inspector@gov.in", "password": "inspector123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_quality_assessor_no_crash():
    """Verify the quality assessor doesn't crash with NameError (contrast_std fix)."""
    # Create a simple test image — should NOT raise any exception
    test_img = np.full((400, 500, 3), 128, dtype=np.uint8)
    cv2.putText(test_img, "TEST LABEL TEXT", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    result = assess_image_quality(test_img)

    # Should return a valid result dict without crashing
    assert "is_acceptable" in result
    assert "quality_score" in result
    assert "metrics" in result
    assert "contrast_std" in result["metrics"]
    assert isinstance(result["metrics"]["contrast_std"], float)


def test_quality_assessor_calibration_sharpness():
    """Verify calibrated sharpness threshold (40.0) differentiates crisp from blurry images."""
    compliant_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    blurry_path = os.path.join(SAMPLE_DIR, "blurry_label.png")

    assert os.path.exists(compliant_path)
    assert os.path.exists(blurry_path)

    img_clean = cv2.imread(compliant_path)
    img_blur = cv2.imread(blurry_path)

    res_clean = assess_image_quality(img_clean)
    res_blur = assess_image_quality(img_blur)

    # Crisp image must pass
    assert res_clean["is_acceptable"] is True
    assert res_clean["quality_score"] >= 60.0
    assert res_clean["metrics"]["sharpness_laplacian"] > 40.0
    assert len(res_clean["rejection_reasons"]) == 0

    # Blurry image must be rejected BEFORE OCR
    assert res_blur["is_acceptable"] is False
    assert res_blur["metrics"]["sharpness_laplacian"] < 40.0
    assert any("blurry" in r.lower() for r in res_blur["rejection_reasons"])
    assert len(res_blur["recommendations"]) == len(PRACTICAL_REUPLOAD_TIPS)


def test_quality_assessor_resolution_and_darkness():
    """Verify rejection for low-resolution and underexposed images."""
    low_res_path = os.path.join(SAMPLE_DIR, "low_res_label.png")
    assert os.path.exists(low_res_path)

    img_lowres = cv2.imread(low_res_path)
    res_lowres = assess_image_quality(img_lowres)

    assert res_lowres["is_acceptable"] is False
    assert any("resolution is too low" in r.lower() for r in res_lowres["rejection_reasons"])

    # Test extreme dark image (< 30 brightness)
    dark_img = np.zeros((400, 500, 3), dtype=np.uint8) + 15
    res_dark = assess_image_quality(dark_img)
    assert res_dark["is_acceptable"] is False
    assert any("too dark" in r.lower() for r in res_dark["rejection_reasons"])


def test_pre_ocr_hard_rejection_api(auth_header):
    """Verify HTTP 422 pre-OCR rejection and that no DB record is created."""
    db = SessionLocal()
    initial_count = db.query(Inspection).count()
    db.close()

    blurry_path = os.path.join(SAMPLE_DIR, "blurry_label.png")
    with open(blurry_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/inspections/upload",
        files={"image": ("blurry_label.png", file_bytes, "image/png")},
        data={"product_name": "Blurry Test Snack", "brand": "TestBrand"},
        headers=auth_header,
    )

    # Must return 422 Unprocessable Entity
    assert res.status_code == 422
    data = res.json()["detail"]
    assert data["code"] == "IMAGE_QUALITY_VALIDATION_FAILED"
    assert "quality_assessment" in data
    assert len(data["rejection_reasons"]) > 0
    assert len(data["recommendations"]) == 7

    # Verify no zombie DB record was inserted
    db = SessionLocal()
    final_count = db.query(Inspection).count()
    db.close()
    assert final_count == initial_count


def test_contextual_numeric_disambiguation():
    """Verify disambiguation of visually confused characters in numeric and text domains."""
    # 0 vs O
    assert disambiguate_numeric_string("1O0") == "100"
    assert disambiguate_numeric_string("25.OO") == "25.00"

    # 1 vs I vs l
    assert disambiguate_numeric_string("l50") == "150"
    assert disambiguate_numeric_string("I00") == "100"

    # 5 vs S
    assert disambiguate_numeric_string("S0") == "50"
    assert disambiguate_numeric_string("2S.50") == "25.50"

    # 8 vs B
    assert disambiguate_numeric_string("B5.00") == "85.00"

    # 2 vs Z
    assert disambiguate_numeric_string("Z50") == "250"

    # 6 vs G
    assert disambiguate_numeric_string("G00") == "600"

    # 0 vs D (new)
    assert disambiguate_numeric_string("D.5") == "0.5"

    # Comma to decimal separator
    assert disambiguate_numeric_string("45,50") == "45.50"

    # Text word corrections
    assert disambiguate_text_string("MADE IN 1NDIA") == "MADE IN INDIA"
    assert disambiguate_text_string("SUNCREST FOODS C0RPORATION") == "SUNCREST FOODS CORPORATION"

    # New text corrections
    assert disambiguate_text_string("ENTERPR1SES") == "ENTERPRISES"
    assert disambiguate_text_string("PR0DUCTS") == "PRODUCTS"


def test_unit_ocr_fixes():
    """Verify OCR error correction in unit strings."""
    assert fix_unit_ocr_errors("q") == "g"
    assert fix_unit_ocr_errors("rnl") == "ml"
    assert fix_unit_ocr_errors("kq") == "kg"
    assert fix_unit_ocr_errors("KG") == "kg"
    assert fix_unit_ocr_errors("ML") == "ml"
    assert fix_unit_ocr_errors("Ltr") == "ltr"


def test_unit_normalization():
    """Verify unit canonicalization."""
    assert normalize_unit("gm") == "g"
    assert normalize_unit("gms") == "g"
    assert normalize_unit("kg") == "kg"
    assert normalize_unit("kgs") == "kg"
    assert normalize_unit("ltr") == "l"
    assert normalize_unit("litres") == "l"
    assert normalize_unit("ml") == "ml"
    assert normalize_unit("pcs") == "pcs"


def test_field_extractors_with_ambiguity():
    """Verify Net Qty, MRP, Date, and FSSAI extraction with disambiguation."""
    # Net Quantity disambiguation: 'lOO g' -> '100 g'
    val_net, ok_net = validate_and_disambiguate_net_quantity("lOO g")
    assert ok_net is True
    assert val_net == "100 g"

    # MRP disambiguation: 'Rs. 2S.OO' -> 25.00
    amt, disp_mrp, ok_mrp = validate_and_disambiguate_mrp("Rs. 2S.OO")
    assert ok_mrp is True
    assert amt == 25.0
    assert disp_mrp == "25.00"

    # Date disambiguation: '08/2O26' -> '08/2026'
    d_val, ok_date = validate_and_disambiguate_date("08/2O26")
    assert ok_date is True
    assert d_val == "08/2026"

    # FSSAI disambiguation: 14 digits with O -> 0
    fssai_str = "1OO15O11OOO234"
    f_val, ok_fssai = validate_and_disambiguate_fssai(fssai_str)
    assert ok_fssai is True
    assert f_val == "10015011000234"


def test_safe_extraction_principle_uncertain_tag():
    """Verify corrupt/unresolvable inputs are tagged as UNCERTAIN instead of hallucinating."""
    # Malformed FSSAI license (wrong length / corrupt chars)
    f_corrupt, f_ok = validate_and_disambiguate_fssai("FSSAI Lic: 199XX88")
    assert f_ok is False

    # Extract fields from OCR text containing uncertain corrupted FSSAI & MRP
    ocr_corrupt = """
    NUTRICRUNCH ALMOND COOKIES
    Manufactured by: Suncrest Foods Pvt. Ltd.
    Net Quantity: ?? g
    MRP: Rs. ###
    Mfg Date: 99/9999
    FSSAI Lic: 10015011000??
    """
    fields = extract_compliance_fields(ocr_corrupt)

    # Verify rule evaluation flags uncertain fields as Fail
    score, status, validations = evaluate_compliance(fields, is_food_product=True)
    assert status == "Non-Compliant"
    assert score < 80.0


def test_cv_variants_generation():
    """Verify generation of 5 multi-pass preprocessing variants A through E."""
    dummy_bgr = np.full((300, 400, 3), 200, dtype=np.uint8)
    cv2.putText(dummy_bgr, "LEGAL METROLOGY", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    variants = generate_preprocessing_variants(dummy_bgr)
    assert "variant_a" in variants
    assert "variant_b" in variants
    assert "variant_c" in variants
    assert "variant_d" in variants
    assert "variant_e" in variants

    # Variant C should be 2.0x upscaled (changed from 1.5x)
    assert variants["variant_c"].shape[0] == int(300 * 2.0)
    assert variants["variant_c"].shape[1] == int(400 * 2.0)

    # Variant E should be 2.5x upscaled
    assert variants["variant_e"].shape[0] == int(300 * 2.5)
    assert variants["variant_e"].shape[1] == int(400 * 2.5)

    # Variant D should be binary (only 0 and 255 values)
    unique_vals = np.unique(variants["variant_d"])
    assert all(v in (0, 255) for v in unique_vals)

    # Test unsharp mask & illumination normalization
    gray = cv2.cvtColor(dummy_bgr, cv2.COLOR_BGR2GRAY)
    sharpened = unsharp_mask(gray)
    assert sharpened.shape == gray.shape

    normalized = normalize_illumination(gray)
    assert normalized.shape == gray.shape


def test_auto_deblur():
    """Verify auto-deblur function handles blur detection and restoration."""
    # Create a sharp image
    sharp_img = np.full((300, 400), 200, dtype=np.uint8)
    cv2.putText(sharp_img, "SHARP TEXT", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)

    # Auto-deblur on sharp image should return similar image (no-op)
    result_sharp = auto_deblur(sharp_img)
    assert result_sharp.shape == sharp_img.shape

    # Create a blurry image
    blurry_img = cv2.GaussianBlur(sharp_img, (15, 15), 5)
    result_blur = auto_deblur(blurry_img)
    assert result_blur.shape == blurry_img.shape

    # The deblurred image should have higher Laplacian variance than the blurry input
    lap_blur = float(cv2.Laplacian(blurry_img, cv2.CV_64F).var())
    lap_restored = float(cv2.Laplacian(result_blur, cv2.CV_64F).var())
    assert lap_restored >= lap_blur


def test_conditional_denoise():
    """Verify conditional denoising preserves clean images and cleans noisy ones."""
    # Clean image should be unchanged
    clean_img = np.full((300, 400), 128, dtype=np.uint8)
    cv2.putText(clean_img, "CLEAN", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)

    result_clean = conditional_denoise(clean_img)
    # Should return the same array (no denoising applied)
    assert np.array_equal(result_clean, clean_img)

    # Noisy image should be denoised
    noisy_img = clean_img.copy()
    noise = np.random.normal(0, 25, noisy_img.shape).astype(np.int16)
    noisy_img = np.clip(noisy_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    result_noisy = conditional_denoise(noisy_img)
    assert result_noisy.shape == noisy_img.shape


def test_trim_blank_borders():
    """Verify border trimming removes blank regions around content."""
    # Create image with content in center and blank borders
    full_img = np.full((600, 800, 3), 255, dtype=np.uint8)
    # Add text in center region
    cv2.putText(full_img, "CENTERED LABEL", (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.rectangle(full_img, (200, 200), (600, 400), (0, 0, 0), 2)

    gray = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)
    trimmed = trim_blank_borders(full_img, gray)

    # Trimmed should be smaller than original
    assert trimmed.shape[0] <= full_img.shape[0]
    assert trimmed.shape[1] <= full_img.shape[1]


def test_levenshtein_similarity():
    """Verify Levenshtein similarity computation for consensus merge."""
    # Identical strings
    assert _levenshtein_similarity("hello", "hello") == 1.0

    # Empty strings
    assert _levenshtein_similarity("", "") == 1.0
    assert _levenshtein_similarity("hello", "") == 0.0

    # Similar strings
    sim = _levenshtein_similarity("MANUFACTURED BY", "MANUFACTUR3D BY")
    assert sim > 0.8

    # Very different strings
    sim_diff = _levenshtein_similarity("ABCDEF", "XYZ123")
    assert sim_diff < 0.5


def test_consensus_merge_picks_longest():
    """Verify consensus merge picks longest text as base, not just highest confidence."""
    from app.ocr.ocr_service import merge_ocr_consensus

    # Pass A: Short text, high confidence
    pass_a = ("SHORT TEXT", 0.95, [{"text": "SHORT TEXT", "confidence": 0.95, "box": [], "source_pass": "a"}])

    # Pass B: Long text, lower confidence
    pass_b = (
        "MANUFACTURED BY SUNCREST FOODS PVT. LTD.\nNET QUANTITY: 100 g\nMRP: Rs. 25.00",
        0.75,
        [{"text": "MANUFACTURED BY SUNCREST FOODS PVT. LTD.", "confidence": 0.75, "box": [], "source_pass": "b"}]
    )

    raw, validated, conf, blocks = merge_ocr_consensus([pass_a, pass_b])

    # Should pick the longer text as base, not the higher-confidence short text
    assert "MANUFACTURED" in raw
    assert "NET QUANTITY" in raw
