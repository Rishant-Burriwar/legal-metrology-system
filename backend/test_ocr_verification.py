import sys
import os
import cv2
import json

# Add backend directory to sys.path
sys.path.insert(0, r"c:\Users\burri\.gemini\antigravity\scratch\legal-metrology-system\backend")

from app.cv_pipeline.preprocessor import process_label_image
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline
from app.cv_pipeline.preprocessor import process_label_image
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline
from app.extraction.extractor import extract_compliance_fields, merge_multi_image_fields
from app.rule_engine.rules import evaluate_compliance

print("=" * 60)
print("TEST 1: inspection_101_1_orig.png (Sprite bottle front)")
print("=" * 60)

storage_dir = r"c:\Users\burri\.gemini\antigravity\scratch\legal-metrology-system\backend\storage\test_debug"
os.makedirs(storage_dir, exist_ok=True)

img_path_1 = r"c:\Users\burri\.gemini\antigravity\scratch\legal-metrology-system\backend\storage\images\inspection_101_1_orig.png"
with open(img_path_1, "rb") as f:
    img_bytes_1 = f.read()

orig_fn_1, crop_fn_1, _, variants_1 = process_label_image(
    image_bytes=img_bytes_1,
    storage_dir=storage_dir,
    inspection_id=999,
    image_index=0,
    debug_mode=True,
)
ocr_res_1 = perform_adaptive_ocr_pipeline(variants_1, variants_1.get("cropped_bgr"))

print(f"Passes executed: {ocr_res_1['passes_executed']}")
print(f"Best orientation: {ocr_res_1['ocr_diagnostics']['best_orientation']}")
print(f"Confidence: {ocr_res_1['ocr_confidence']}")
print(f"Blocks detected: {len(ocr_res_1['blocks'])}")
print("Raw OCR Text:")
print(ocr_res_1["raw_ocr_text"])

fields_1 = extract_compliance_fields(ocr_res_1["raw_ocr_text"], ocr_res_1["validated_ocr_text"])
print("\nExtracted Compliance Fields:")
for k, v in fields_1.items():
    if isinstance(v, dict) and v.get("status") != "not_found":
        print(f"  {k}: {v.get('value')} (status: {v.get('status')})")

print("\n" + "=" * 60)
print("TEST 2: inspection_101_orig.png (Vertical sweetener declaration)")
print("=" * 60)

img_path_2 = r"c:\Users\burri\.gemini\antigravity\scratch\legal-metrology-system\backend\storage\images\inspection_101_orig.png"
with open(img_path_2, "rb") as f:
    img_bytes_2 = f.read()

orig_fn_2, crop_fn_2, _, variants_2 = process_label_image(
    image_bytes=img_bytes_2,
    storage_dir=storage_dir,
    inspection_id=999,
    image_index=1,
    debug_mode=True,
)
ocr_res_2 = perform_adaptive_ocr_pipeline(variants_2, variants_2.get("cropped_bgr"))

print(f"Passes executed: {ocr_res_2['passes_executed']}")
print(f"Best orientation: {ocr_res_2['ocr_diagnostics']['best_orientation']}")
print(f"Confidence: {ocr_res_2['ocr_confidence']}")
print(f"Blocks detected: {len(ocr_res_2['blocks'])}")
print("Raw OCR Text:")
print(ocr_res_2["raw_ocr_text"])

fields_2 = extract_compliance_fields(ocr_res_2["raw_ocr_text"], ocr_res_2["validated_ocr_text"])
print("\nExtracted Compliance Fields:")
for k, v in fields_2.items():
    if isinstance(v, dict) and v.get("status") != "not_found":
        print(f"  {k}: {v.get('value')} (status: {v.get('status')})")

print("\n" + "=" * 60)
print("TEST 3: Multi-Image Deduplication & Fusion")
print("=" * 60)
merged = merge_multi_image_fields(
    all_extracted=[fields_1, fields_2],
    all_ocr_confidences=[ocr_res_1["ocr_confidence"], ocr_res_2["ocr_confidence"]],
    views=["Front", "Side"],
    image_paths=["/storage/images/inspection_101_1_orig.png", "/storage/images/inspection_101_orig.png"],
    all_blocks=[ocr_res_1["blocks"], ocr_res_2["blocks"]],
)
print("Merged Extracted Fields:")
for k, v in merged.items():
    if isinstance(v, dict) and v.get("status") != "not_found" and not k.startswith("_"):
        print(f"  {k}: {v.get('value')} [source: {v.get('source_view')}, bbox: {v.get('bounding_box')}]")

print("\n" + "=" * 60)
print("TEST 4: Compliance Rule Evaluation")
print("=" * 60)
rule_input = {k: v for k, v in merged.items() if not k.startswith("_")}
score, status, results = evaluate_compliance(rule_input, is_food_product=True)
print(f"Compliance Score: {score:.1f}% | Overall Status: {status}")
for r in results:
    print(f"  [{r['status']}] {r['rule_code']}: {r['description']}")
