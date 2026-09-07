import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.gemini_service import get_gemini_service, GeminiService
from app.rule_engine.rules import evaluate_compliance

client = TestClient(app)
SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_images"))


@pytest.fixture(scope="module")
def auth_header():
    res = client.post("/auth/login", json={"email": "inspector@gov.in", "password": "inspector123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_gemini_service_configuration():
    """Verify Gemini service loads configuration correctly."""
    svc = get_gemini_service()
    assert svc.is_configured is True
    assert svc.api_key is not None
    assert "gemini" in svc.model


def test_gemini_packaging_visual_analysis():
    """Verify Gemini multimodal image quality and visual packaging analysis."""
    svc = get_gemini_service()
    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        img_bytes = f.read()

    analysis = svc.analyze_packaging_image(img_bytes)
    assert analysis is not None
    assert "packaging_type" in analysis
    assert "legibility_score" in analysis
    assert isinstance(analysis["legibility_score"], (int, float))
    assert analysis["legibility_score"] >= 60
    assert "visual_observations" in analysis
    assert len(analysis["visual_observations"]) > 0


def test_gemini_statutory_field_extraction_compliant():
    """Verify Gemini statutory extraction on compliant biscuit label."""
    svc = get_gemini_service()
    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        img_bytes = f.read()

    result = svc.extract_statutory_fields(img_bytes, is_food_product=True)
    assert result["success"] is True
    assert len(result["verbatim_text"]) > 20

    fields = result["fields"]
    # Check all 7 statutory fields
    assert fields["manufacturer_details"]["status"] == "found"
    assert "Suncrest" in fields["manufacturer_details"]["value"]

    assert fields["net_quantity"]["status"] == "found"
    assert "250" in fields["net_quantity"]["value"]

    assert fields["mrp"]["status"] == "found"
    assert fields["mrp"]["taxes_included"] is True

    assert fields["manufacture_date"]["status"] == "found"

    assert fields["customer_care"]["status"] == "found"
    assert fields["customer_care"]["phone"] is not None

    assert fields["fssai_license"]["status"] == "found"
    assert fields["fssai_license"]["value"] == "10015011000234"

    assert fields["country_of_origin"]["status"] == "found"

    # Evaluate against Legal Metrology Rules, 2011
    score, status, validations = evaluate_compliance(fields, is_food_product=True)
    assert score == 100.0
    assert status == "Compliant"


def test_gemini_statutory_field_extraction_non_compliant():
    """Verify Gemini detects missing tax clause and missing customer care on non-compliant sample."""
    svc = get_gemini_service()
    sample_path = os.path.join(SAMPLE_DIR, "non_compliant_label.png")
    with open(sample_path, "rb") as f:
        img_bytes = f.read()

    result = svc.extract_statutory_fields(img_bytes, is_food_product=True)
    assert result["success"] is True
    fields = result["fields"]

    # Non-compliant label has MRP but taxes clause is NOT declared
    assert fields["mrp"]["taxes_included"] is False

    score, status, validations = evaluate_compliance(fields, is_food_product=True)
    assert score < 100.0
    # Rule LM-03 must fail because taxes are not included
    mrp_rule = next(v for v in validations if v["rule_code"] == "LM-03")
    assert mrp_rule["status"] == "Fail"


def test_hybrid_consensus_merge():
    """Verify hybrid consensus merge unifies fields from Gemini and local OCR."""
    svc = get_gemini_service()

    gemini_fields = {
        "manufacturer_details": {"value": "Suncrest Foods Pvt. Ltd., Okhla", "status": "found"},
        "net_quantity": {"value": "250 g", "status": "found"},
        "mrp": {"value": "₹ 85.00 (incl. of all taxes)", "taxes_included": True, "status": "found"},
        "fssai_license": {"value": "10015011000234", "status": "found"},
        "customer_care": {"value": "Phone: 1800-112-4999", "status": "found"},
    }

    local_ocr_fields = {
        "manufacturer_details": {"value": "Suncrest Foods Pvt Ltd", "status": "low_confidence"},
        "net_quantity": {"value": "250 g", "status": "found"},
        "mrp": {"value": "₹ 85.00", "taxes_included": False, "status": "low_confidence"},
        "fssai_license": {"value": None, "status": "not_found"},
        "country_of_origin": {"value": "India", "status": "found"},
    }

    merged = svc.hybrid_consensus_merge(gemini_fields, local_ocr_fields)
    assert merged["net_quantity"]["consensus"] == "verified"
    assert merged["fssai_license"]["status"] == "found"
    assert merged["fssai_license"]["consensus"] == "gemini_exclusive"
    assert merged["country_of_origin"]["status"] == "found"
    assert merged["country_of_origin"]["consensus"] == "local_exclusive"
    assert "_consensus_metadata" in merged


def test_api_upload_with_gemini_engine(auth_header):
    """Test full upload inspection API call using Gemini AI engine."""
    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/inspections/upload",
        files={"images": ("compliant_label.png", file_bytes, "image/png")},
        data={
            "product_name": "NutriCrunch Cookies",
            "brand": "Suncrest",
            "is_food_product": "true",
            "ai_engine": "gemini",
        },
        headers=auth_header,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "Compliant"
    assert data["compliance_score"] == 100.0
    assert data["extracted_data"]["_ai_engine"] == "Gemini Multimodal Vision AI"
    assert "_gemini_analysis" in data["extracted_data"] or "gemini_analysis" in (data.get("quality_assessment") or {})


def test_api_upload_with_hybrid_engine(auth_header):
    """Test upload inspection API call using Hybrid AI Consensus engine."""
    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/inspections/upload",
        files={"images": ("compliant_label.png", file_bytes, "image/png")},
        data={
            "product_name": "NutriCrunch Cookies",
            "brand": "Suncrest",
            "is_food_product": "true",
            "ai_engine": "hybrid",
        },
        headers=auth_header,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "Compliant"
    assert data["extracted_data"]["_ai_engine"] == "Hybrid AI Consensus (Gemini + EasyOCR)"


def test_preprocess_gemini_analyze_endpoint():
    """Test the /preprocess/gemini-analyze endpoint for ImageLab."""
    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/preprocess/gemini-analyze",
        files={"image": ("compliant_label.png", file_bytes, "image/png")},
        data={"is_food_product": "true"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "visual_analysis" in data
    assert "extraction" in data
    assert data["engine"] == "Gemini Multimodal AI"
