"""
Quick CLI test: process a label image through the full pipeline and print extracted fields.
Usage: python test_image_pipeline.py <path_to_image>
"""
import sys
import os
import cv2
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.cv_pipeline.quality_assessor import assess_image_quality
from app.cv_pipeline.preprocessor import process_label_image
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline
from app.extraction.extractor import extract_compliance_fields
from app.rule_engine.rules import evaluate_compliance


def process_image(image_path: str):
    if not os.path.exists(image_path):
        print(f"ERROR: File not found: {image_path}")
        return

    print(f"\n{'='*70}")
    print(f"  Processing: {os.path.basename(image_path)}")
    print(f"{'='*70}\n")

    # Read image
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    original_bgr = cv2.imdecode(
        __import__("numpy").frombuffer(image_bytes, __import__("numpy").uint8),
        cv2.IMREAD_COLOR
    )

    # Step 1: Quality Assessment
    print("[1/5] Quality Assessment...")
    quality = assess_image_quality(original_bgr)
    print(f"  Acceptable: {quality['is_acceptable']}")
    print(f"  Quality Score: {quality['quality_score']}")
    print(f"  Sharpness (Laplacian): {quality['metrics'].get('sharpness_laplacian', 'N/A')}")
    if quality['rejection_reasons']:
        print(f"  Rejections: {quality['rejection_reasons']}")
    print()

    if not quality['is_acceptable']:
        print("  ⚠ Image rejected by quality gate. Proceeding anyway for testing...\n")

    # Step 2: CV Preprocessing
    print("[2/5] CV Preprocessing (deskew, crop, variants)...")
    storage_dir = os.path.join(os.path.dirname(__file__), "storage", "images")
    orig_fn, crop_fn, enhanced, variants = process_label_image(
        image_bytes=image_bytes,
        storage_dir=storage_dir,
        inspection_id=9999,
    )
    print(f"  Variants generated: {list(variants.keys())}")
    for k, v in variants.items():
        print(f"    {k}: {v.shape}")
    print()

    # Step 3: OCR
    print("[3/5] Multi-pass Adaptive OCR...")
    ocr_result = perform_adaptive_ocr_pipeline(variants)
    print(f"  Passes executed: {ocr_result['passes_executed']}")
    print(f"  OCR Confidence: {ocr_result['ocr_confidence']}")
    print(f"  Retry count: {ocr_result['ocr_retry_count']}")
    print(f"\n  --- Raw OCR Text ---")
    for line in ocr_result['raw_ocr_text'].splitlines():
        if line.strip():
            print(f"  | {line.strip()}")
    print()

    # Step 4: Field Extraction
    print("[4/5] Legal Metrology Field Extraction...")
    fields = extract_compliance_fields(
        raw_ocr_text=ocr_result['raw_ocr_text'],
        validated_ocr_text=ocr_result['validated_ocr_text'],
    )

    print()
    field_labels = {
        "manufacturer_details": "Manufacturer",
        "net_quantity": "Net Quantity",
        "mrp": "MRP",
        "manufacture_date": "Mfg Date",
        "customer_care": "Customer Care",
        "fssai_license": "FSSAI Lic No",
        "country_of_origin": "Country of Origin",
    }
    for key, label in field_labels.items():
        field = fields.get(key, {})
        value = field.get("value", "—")
        status = field.get("status", "not_found")
        status_icon = {"found": "[OK]", "low_confidence": "[~ ]", "uncertain": "[? ]", "not_found": "[X ]"}
        icon = status_icon.get(status, "[? ]")
        print(f"  {icon} {label}: {value}")
    print()

    # Step 5: Compliance Evaluation
    print("[5/5] Compliance Evaluation...")
    score, overall_status, validations = evaluate_compliance(fields, is_food_product=True)
    print(f"  Compliance Score: {score}%")
    print(f"  Overall Status: {overall_status}")
    print()
    for v in validations:
        icon = "✓" if v["status"] == "Pass" else "✗"
        print(f"  [{icon}] {v['rule_code']}: {v['description'][:80]}")

    print(f"\n{'='*70}")
    print(f"  RESULT: {overall_status} ({score}%)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_image_pipeline.py <path_to_image>")
        print("Example: python test_image_pipeline.py sample_images/compliant_label.png")
        sys.exit(1)

    process_image(sys.argv[1])
