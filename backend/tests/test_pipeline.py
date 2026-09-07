import os
import pytest
from app.cv_pipeline.preprocessor import process_label_image
from app.extraction.extractor import extract_compliance_fields
from app.rule_engine.rules import evaluate_compliance
from app.reports.pdf_generator import generate_inspection_pdf
from datetime import datetime


def test_extraction_rules_and_pdf():
    # 1. Test extraction with simulated fully-compliant OCR text
    compliant_ocr = """
    NUTRICRUNCH ALMOND COOKIES
    Manufactured by: Suncrest Foods Pvt. Ltd., Plot 42, Okhla Ind Area, New Delhi - 110020
    Net Quantity: 250 g
    MRP: Rs. 85.00 (incl. of all taxes)
    Mfg Date: 08/2026
    Customer Care: 1800-112-4999, care@suncrestfoods.in
    FSSAI Lic No: 10015011000234
    Country of Origin: India
    """

    fields = extract_compliance_fields(compliant_ocr)
    assert fields["net_quantity"]["status"] == "found"
    assert "250 g" in fields["net_quantity"]["value"]
    assert fields["mrp"]["taxes_included"] is True
    assert fields["fssai_license"]["status"] == "found"
    assert fields["fssai_license"]["value"] == "10015011000234"
    assert fields["customer_care"]["phone"] is not None
    assert fields["customer_care"]["email"] is not None

    score, status, validations = evaluate_compliance(fields, is_food_product=True)
    assert score == 100.0
    assert status == "Compliant"
    assert all(v["status"] == "Pass" for v in validations)

    # 2. Test extraction with non-compliant text
    non_compliant_ocr = """
    CHOCODELIGHT PREMIUM BAR
    Net Quantity: 50 g
    MRP: Rs. 40.00
    Mfg Date: 12/2025
    """

    nc_fields = extract_compliance_fields(non_compliant_ocr)
    assert nc_fields["mrp"]["taxes_included"] is False
    assert nc_fields["customer_care"]["status"] == "not_found"

    nc_score, nc_status, nc_validations = evaluate_compliance(nc_fields, is_food_product=True)
    assert nc_score < 80.0
    assert nc_status == "Non-Compliant"

    # 3. Test PDF generation produces valid binary content
    pdf_bytes = generate_inspection_pdf(
        inspection_id=1,
        created_at=datetime.utcnow(),
        product_name="NutriCrunch Cookies",
        brand="Suncrest Foods",
        overall_status="Compliant",
        compliance_score=100.0,
        violations=validations,
        extracted_data=fields,
    )
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_cv_pipeline_with_sample_image():
    sample_img_path = os.path.join(
        os.path.dirname(__file__), "..", "sample_images", "compliant_label.png"
    )
    assert os.path.exists(sample_img_path)

    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    test_storage = os.path.join(os.path.dirname(__file__), "..", "storage", "images")
    orig_file, crop_file, enhanced, variants = process_label_image(img_bytes, test_storage, 999)

    assert os.path.exists(os.path.join(test_storage, orig_file))
    assert os.path.exists(os.path.join(test_storage, crop_file))
    assert enhanced is not None
    assert len(enhanced.shape) == 2  # Grayscale
    assert "variant_a" in variants
    assert "variant_b" in variants
    assert "variant_c" in variants
    assert len(enhanced.shape) == 2  # Grayscale
