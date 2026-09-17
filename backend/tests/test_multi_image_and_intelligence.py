import os
import cv2
import pytest
from app.extraction.extractor import merge_multi_image_fields
from app.rule_engine.rules import evaluate_compliance
from app.product_intelligence.service import ProductIntelligenceService
from app.cv_pipeline.panorama_stitcher import stitch_package_images
from app.cv_pipeline.video_inspector import process_inspection_video
from app.reports.pdf_generator import generate_inspection_pdf
from datetime import datetime, timezone


def test_merge_multi_image_fields_deduplication():
    face_front = {
        "net_quantity": {"value": "250 g", "status": "found", "confidence": 0.95},
        "mrp": {"value": "Rs. 85.00 (incl. of all taxes)", "status": "found", "confidence": 0.94},
        "manufacture_date": {"value": None, "status": "not_found", "confidence": 0.0},
    }
    face_back = {
        "net_quantity": {"value": "250 g", "status": "found", "confidence": 0.88},
        "manufacture_date": {"value": "08/2026", "status": "found", "confidence": 0.96},
        "manufacturer_details": {"value": "Suncrest Foods Pvt. Ltd., Okhla, New Delhi", "status": "found", "confidence": 0.93},
        "fssai_license": {"value": "10015011000234", "status": "found", "confidence": 0.98},
    }
    face_side = {
        "customer_care": {"value": "1800-112-4999, care@suncrestfoods.in", "status": "found", "confidence": 0.91},
        "country_of_origin": {"value": "India", "status": "found", "confidence": 0.97},
    }

    all_extracted = [face_front, face_back, face_side]
    views = ["Front Label", "Back Panel", "Side Panel"]
    image_paths = ["/storage/images/front.png", "/storage/images/back.png", "/storage/images/side.png"]

    merged = merge_multi_image_fields(all_extracted, views=views, image_paths=image_paths)

    assert merged["net_quantity"]["status"] == "found"
    assert merged["net_quantity"]["value"] == "250 g"
    assert merged["net_quantity"]["source_view"] == "Front Label"

    assert merged["manufacture_date"]["status"] == "found"
    assert merged["manufacture_date"]["value"] == "08/2026"
    assert merged["manufacture_date"]["source_view"] == "Back Panel"

    assert merged["customer_care"]["status"] == "found"
    assert merged["customer_care"]["source_view"] == "Side Panel"

    assert "fssai_license" in merged
    assert "country_of_origin" in merged


def test_merge_multi_image_discrepancy_detection():
    face_a = {"mrp": {"value": "Rs. 50.00", "status": "found", "confidence": 0.95}}
    face_b = {"mrp": {"value": "Rs. 60.00", "status": "found", "confidence": 0.90}}

    merged = merge_multi_image_fields([face_a, face_b], views=["Front Face", "Top Flap"])
    assert merged["mrp"]["discrepancy_detected"] is True
    assert "Values differ across facets" in merged["mrp"]["discrepancy_note"]


def test_evidence_linking_in_rules():
    extracted = {
        "mrp": {
            "value": "Rs. 40.00",  # missing incl of all taxes -> violation
            "status": "found",
            "source_view": "Front Panel",
            "evidence_image_path": "/storage/front.png",
            "bounding_box": [10, 20, 100, 40],
            "confidence": 0.92,
        },
        "net_quantity": {
            "value": "100 g",
            "status": "found",
            "source_view": "Front Panel",
            "evidence_image_path": "/storage/front.png",
            "bounding_box": [15, 60, 90, 80],
            "confidence": 0.95,
        },
        "manufacture_date": {"value": "10/2026", "status": "found", "source_view": "Back Panel"},
        "manufacturer_details": {"value": "ABC Foods Ltd, Mumbai", "status": "found", "source_view": "Back Panel"},
        "customer_care": {"value": "care@abcfoods.com", "status": "found", "source_view": "Back Panel"},
        "fssai_license": {"value": "10012345678901", "status": "found", "source_view": "Back Panel"},
        "country_of_origin": {"value": "India", "status": "found", "source_view": "Back Panel"},
    }

    compliance_score, overall_status, violations = evaluate_compliance(extracted, is_food_product=True)

    assert overall_status == "Non-Compliant"

    # Rule LM-03 is MRP verification
    mrp_v = next((v for v in violations if v["rule_code"] == "LM-03"), None)
    assert mrp_v is not None
    assert mrp_v["status"] == "Fail"
    assert mrp_v["source_view"] == "Front Panel"
    assert mrp_v["detected_value"] == "Rs. 40.00"
    assert "inclusive of all taxes" in mrp_v["expected_condition"].lower()


def test_product_intelligence_decoding():
    ocr_text = """
    NUTRICRUNCH COOKIES
    Ingredients: Refined Wheat Flour, Sugar, Edible Vegetable Oil, Almonds (8%),
    Emulsifier (INS 322 - Soy Lecithin), Acidity Regulator (INS 330),
    Artificial Color (INS 102), Preservative (INS 211).
    Allergen Advice: Contains Wheat, Tree Nuts, Soy.
    Per 100g: Energy 480 kcal, Protein 7.2g, Total Fat 20g, Sodium 240mg.
    """

    pi = ProductIntelligenceService.analyze_package(ocr_text, is_food=True)

    assert pi["ingredients_found"] is True
    assert pi["total_ingredients_count"] > 0

    decoded_codes = [a["identifier"] for a in pi["additives"]]
    assert "INS 322" in decoded_codes
    assert "INS 330" in decoded_codes
    assert "INS 102" in decoded_codes
    assert "INS 211" in decoded_codes

    ins_102 = next(a for a in pi["additives"] if a["identifier"] == "INS 102")
    assert ins_102["risk_level"] in ["orange", "yellow"]

    allergen_names = [a["name"].lower() for a in pi["allergens"]]
    assert any("wheat" in n or "gluten" in n for n in allergen_names)
    assert any("soy" in n for n in allergen_names)

    assert pi["nutritional_panel"] is not None
    assert pi["nutritional_panel"]["detected"] is True

    assert "Product Intelligence is strictly informational" in pi["disclaimer"]


def test_panorama_stitcher_graceful_handling():
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_images"))
    p1 = os.path.join(sample_dir, "cylinder_p1.png")
    p2 = os.path.join(sample_dir, "cylinder_p2.png")
    p3 = os.path.join(sample_dir, "cylinder_p3.png")

    if os.path.exists(p1) and os.path.exists(p2):
        imgs = [cv2.imread(p) for p in [p1, p2, p3] if os.path.exists(p)]
        res = stitch_package_images(imgs, storage_dir=sample_dir, inspection_id=888)
        assert res["status"] in ["success", "fallback"]
        assert "overlap_confidence" in res


def test_video_inspector_keyframing():
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_images"))
    vpath = os.path.join(sample_dir, "sample_inspection_video.mp4")

    if os.path.exists(vpath):
        res = process_inspection_video(vpath, storage_dir=sample_dir, inspection_id=777, max_keyframes=6)
        assert len(res["keyframes"]) > 0
        assert res["telemetry"]["frames_captured"] > 0
        assert "video_duration_seconds" in res["telemetry"]


def test_7_section_pdf_generation():
    violations = [
        {
            "rule_code": "LM-01",
            "description": "Manufacturer details declared",
            "severity": "Major",
            "status": "Pass",
            "source_view": "Back Panel",
            "detected_value": "Suncrest Foods Ltd.",
            "expected_condition": "Full manufacturer name and address",
        },
        {
            "rule_code": "LM-03",
            "description": "Maximum Retail Price (MRP)",
            "severity": "Critical",
            "status": "Fail",
            "source_view": "Front Panel",
            "detected_value": "Rs. 40.00",
            "expected_condition": "Must include 'incl. of all taxes'",
        }
    ]

    extracted_data = {
        "net_quantity": {"value": "250 g", "status": "found", "source_view": "Front"},
        "mrp": {"value": "Rs. 40.00", "status": "found", "source_view": "Front"},
    }

    product_intelligence = {
        "ingredients_found": True,
        "total_ingredients_count": 5,
        "total_additives_count": 2,
        "additives": [
            {
                "identifier": "INS 322",
                "common_name": "Lecithin",
                "function": "Emulsifier",
                "risk_level": "green",
                "regulatory_status": "Permitted",
                "concerns": "GRAS",
            }
        ],
        "allergens": [{"name": "Wheat (Gluten)", "type": "explicit", "advisory": "Contains Wheat"}],
        "disclaimer": "Informational advisory notice.",
    }

    pdf_bytes = generate_inspection_pdf(
        inspection_id=999,
        created_at=datetime.now(timezone.utc),
        product_name="Test Compliance Product",
        brand="Suncrest Foods",
        overall_status="Non-Compliant",
        compliance_score=82.5,
        violations=violations,
        extracted_data=extracted_data,
        inspection_mode="multi_image",
        product_intelligence=product_intelligence,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")
