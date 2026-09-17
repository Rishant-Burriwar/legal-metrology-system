import os
import json
import logging
import tempfile
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import Inspection, Violation, User
from app.schemas.schemas import InspectionResponse, InspectionSummary, InspectorOption
from app.auth.dependencies import get_current_user
from app.cv_pipeline.quality_assessor import assess_image_quality
from app.cv_pipeline.preprocessor import process_label_image
from app.cv_pipeline.panorama_stitcher import stitch_package_images
from app.cv_pipeline.video_inspector import process_inspection_video
from app.product_intelligence.service import analyze_product_intelligence
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline
from app.extraction.extractor import extract_compliance_fields, merge_multi_image_fields
from app.rule_engine.rules import evaluate_compliance
from app.reports.pdf_generator import generate_inspection_pdf
from app.services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspections", tags=["Inspections"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "images"))
MAX_IMAGES = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_image(image_bytes: bytes) -> Optional[np.ndarray]:
    """Decode raw bytes to a BGR numpy array. Returns None on failure."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


async def _read_upload(upload: UploadFile) -> bytes:
    content = await upload.read()
    await upload.seek(0)
    return content


# ---------------------------------------------------------------------------
# Multi-image upload endpoint
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=InspectionResponse)
async def upload_and_inspect(
    request: Request,
    images: Optional[List[UploadFile]] = File(None, description="1–8 label photos of the same product"),
    image: Optional[UploadFile] = File(None, description="Single label photo (backward compatibility)"),
    views: Optional[Any] = Form(None, description="List, JSON array, or comma-separated list of package view names"),
    inspection_mode: str = Form("multi_image", description="'multi_image' | 'panorama'"),
    product_name: str = Form("Packaged Commodity"),
    brand: str = Form("Generic Brand"),
    is_food_product: bool = Form(True),
    ai_engine: str = Form("gemini", description="Vision engine: 'gemini' | 'hybrid' | 'local'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified multi-image inspection pipeline with Gemini Multimodal AI,
    360° Panorama unwrap, and Product Intelligence:

    Accepts up to 8 photos of the same product label (Front, Back, Sides, Top, Bottom, etc.).
    For each acceptable image:
      1. Pre-OCR Quality Gate (blur, brightness, resolution, contrast)
      2. Gemini Multimodal Visual Packaging Analysis
      3. OpenCV Preprocessing — 8 variants (A–H) & contour cropping
      4. Text & Statutory Field Extraction (Gemini AI, Hybrid Consensus, or Local OCR)
    Final steps:
      - 360° Panorama stitching attempt with non-breaking fallback
      - Intelligent multi-view fusion and deduplication with evidence coordinates
      - Rule Engine evaluation against Legal Metrology Rules, 2011 (LM-01..LM-07)
      - Product Intelligence analysis (ingredients, additives, allergens)
      - Audit trail persistence and report generation
    """
    # RBAC check: Viewers cannot perform inspections
    if current_user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers have read-only access and are not authorized to inspect products.",
        )

    # Normalize images list from either 'images' or legacy 'image'
    upload_list: List[UploadFile] = []
    if images:
        upload_list.extend(images)
    elif image:
        upload_list.append(image)

    # Robust multi-part intake: inspect form fields in case images were submitted under alternate keys or array notation
    try:
        form = await request.form()
        for k, v in form.multi_items():
            if isinstance(v, UploadFile) and v not in upload_list:
                c_type = (v.content_type or "").lower()
                fname = (v.filename or "").lower()
                if c_type.startswith("image/") or any(fname.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
                    upload_list.append(v)
    except Exception as e:
        logger.debug(f"Form inspection fallback error: {e}")

    if not upload_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required.",
        )

    if len(upload_list) > MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_IMAGES} images allowed per inspection.",
        )

    # Parse view labels if provided (supports List[str], JSON string, or comma-separated)
    views_list: List[str] = []
    if views:
        if isinstance(views, list):
            views_list = [str(v).strip() for v in views if str(v).strip()]
        elif isinstance(views, str):
            try:
                parsed = json.loads(views)
                if isinstance(parsed, list):
                    views_list = [str(v).strip() for v in parsed if str(v).strip()]
                else:
                    views_list = [str(parsed).strip()]
            except Exception:
                views_list = [v.strip() for v in views.split(",") if v.strip()]

    default_views = ["Front", "Back", "Left Side", "Right Side", "Top", "Bottom", "Batch Panel", "Close-up"]

    # Validate content types upfront
    for img in upload_list:
        if not (img.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{img.filename}' is not a valid image (PNG, JPEG, etc.).",
            )

    gemini_svc = get_gemini_service()
    use_gemini = (ai_engine.lower() in ("gemini", "hybrid")) and gemini_svc.is_configured
    ai_engine_label = (
        "Gemini Multimodal Vision AI"
        if ai_engine.lower() == "gemini" and use_gemini
        else (
            "Hybrid AI Consensus (Gemini + EasyOCR)"
            if ai_engine.lower() == "hybrid" and use_gemini
            else "Local OpenCV + EasyOCR"
        )
    )

    # -----------------------------------------------------------------------
    # Phase 1 — Quality Gate for all images
    # -----------------------------------------------------------------------
    image_bytes_list: List[bytes] = []
    decoded_bgr_list: List[np.ndarray] = []
    quality_results: List[dict] = []
    accepted_indices: List[int] = []

    for idx, upload in enumerate(upload_list):
        img_bytes = await _read_upload(upload)
        if len(img_bytes) == 0:
            logger.warning(f"Image #{idx + 1} is empty — skipping.")
            continue

        bgr = _decode_image(img_bytes)
        if bgr is None:
            logger.warning(f"Image #{idx + 1} could not be decoded — skipping.")
            continue

        qr = assess_image_quality(bgr)
        quality_results.append(qr)
        image_bytes_list.append(img_bytes)
        decoded_bgr_list.append(bgr)

        if qr["is_acceptable"]:
            accepted_indices.append(len(image_bytes_list) - 1)
        else:
            logger.warning(
                f"Image #{idx + 1} failed quality gate: {qr['rejection_reasons']}"
            )

    # If NO image passed quality gate, return rich rejection error
    if not accepted_indices:
        first_qr = quality_results[0] if quality_results else {}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "IMAGE_QUALITY_VALIDATION_FAILED",
                "message": (
                    f"None of the {len(upload_list)} uploaded image(s) passed the pre-OCR quality gate. "
                    "Please retake the photos with better lighting and focus."
                ),
                "rejection_reasons": first_qr.get("rejection_reasons", []),
                "quality_assessment": first_qr,
                "recommendations": first_qr.get("recommendations", []),
            },
        )

    # Best quality score across accepted images
    best_quality_score = max(quality_results[i]["quality_score"] for i in accepted_indices)
    best_quality_result = dict(
        max((quality_results[i] for i in accepted_indices), key=lambda q: q["quality_score"])
    )

    # Run Gemini packaging visual analysis if enabled
    if use_gemini and accepted_indices:
        try:
            primary_img_bytes = image_bytes_list[accepted_indices[0]]
            gemini_vis = gemini_svc.analyze_packaging_image(primary_img_bytes)
            best_quality_result["gemini_analysis"] = gemini_vis
            logger.info(f"Gemini visual analysis: {gemini_vis.get('packaging_type')}, legibility={gemini_vis.get('legibility_score')}")
        except Exception as e:
            logger.warning(f"Gemini visual analysis failed: {e}")

    # -----------------------------------------------------------------------
    # Phase 2 — Create inspection record
    # -----------------------------------------------------------------------
    inspection = Inspection(
        inspector_id=current_user.id,
        product_name=product_name.strip() or "Packaged Commodity",
        brand=brand.strip() or "Generic Brand",
        image_path="",
        inspection_mode=inspection_mode,
        quality_score=best_quality_score,
        quality_assessment=best_quality_result,
        compliance_score=0.0,
        overall_status="Processing",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    try:
        # -----------------------------------------------------------------------
        # Phase 3 — Per-image preprocessing, OCR & view records
        # -----------------------------------------------------------------------
        all_extracted: List[dict] = []
        all_ocr_confidences: List[float] = []
        all_raw_texts: List[str] = []
        all_blocks: List[List[dict]] = []
        product_images_records: List[dict] = []

        first_orig_url = ""
        first_crop_url = ""

        for pos_idx, orig_idx in enumerate(accepted_indices):
            img_bytes = image_bytes_list[orig_idx]
            view_label = views_list[orig_idx] if orig_idx < len(views_list) else (
                default_views[orig_idx] if orig_idx < len(default_views) else f"Angle {orig_idx + 1}"
            )

            logger.info(
                f"Inspection #{inspection.id}: Processing view '{view_label}' (#{orig_idx + 1}) (Engine: {ai_engine_label})"
            )

            # 3a. OpenCV preprocessing (variants A–H & contour cropping)
            orig_fn, crop_fn, enhanced_gray, variants = process_label_image(
                image_bytes=img_bytes,
                storage_dir=STORAGE_DIR,
                inspection_id=inspection.id,
                image_index=orig_idx,
            )

            orig_url = f"/storage/images/{orig_fn}"
            crop_url = f"/storage/images/{crop_fn}"

            if not first_orig_url:
                first_orig_url = orig_url
                first_crop_url = crop_url

            crop_bgr_path = os.path.join(STORAGE_DIR, crop_fn)
            cropped_bgr = cv2.imread(crop_bgr_path) if os.path.exists(crop_bgr_path) else None

            # 3b. Extraction according to selected AI Engine
            blocks_for_image = []
            if ai_engine.lower() == "gemini" and use_gemini:
                logger.info(f"Running Gemini Multimodal Vision extraction for '{view_label}'...")
                g_res = gemini_svc.extract_statutory_fields(img_bytes, is_food_product=is_food_product)
                if g_res.get("success"):
                    raw_ocr_text = g_res.get("verbatim_text", "")
                    validated_ocr_text = raw_ocr_text
                    ocr_confidence = g_res.get("confidence", 0.95)
                    extracted = g_res.get("fields", {})
                else:
                    logger.warning("Gemini extraction failed, falling back to local adaptive OCR.")
                    ocr_result = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
                    raw_ocr_text = ocr_result["raw_ocr_text"]
                    validated_ocr_text = ocr_result["validated_ocr_text"]
                    ocr_confidence = ocr_result["ocr_confidence"]
                    blocks_for_image = ocr_result.get("blocks", [])
                    extracted = extract_compliance_fields(raw_ocr_text, validated_ocr_text)

            elif ai_engine.lower() == "hybrid" and use_gemini:
                logger.info(f"Running Hybrid Consensus for '{view_label}'...")
                ocr_result = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
                local_extracted = extract_compliance_fields(ocr_result["raw_ocr_text"], ocr_result["validated_ocr_text"])
                blocks_for_image = ocr_result.get("blocks", [])

                g_res = gemini_svc.extract_statutory_fields(img_bytes, is_food_product=is_food_product)
                g_fields = g_res.get("fields", {}) if g_res.get("success") else {}
                g_text = g_res.get("verbatim_text", "")

                extracted = gemini_svc.hybrid_consensus_merge(
                    gemini_fields=g_fields,
                    local_ocr_fields=local_extracted,
                    gemini_conf=g_res.get("confidence", 0.95),
                    local_conf=ocr_result["ocr_confidence"],
                )
                raw_ocr_text = f"=== GEMINI VISION TRANSCRIPT ({view_label}) ===\n{g_text}\n\n=== LOCAL OCR TRANSCRIPT ===\n{ocr_result['raw_ocr_text']}"
                validated_ocr_text = raw_ocr_text
                ocr_confidence = max(g_res.get("confidence", 0.95), ocr_result["ocr_confidence"])

            else:
                # Local offline pipeline (OpenCV + EasyOCR + Tesseract)
                ocr_result = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
                raw_ocr_text = ocr_result["raw_ocr_text"]
                validated_ocr_text = ocr_result["validated_ocr_text"]
                ocr_confidence = ocr_result["ocr_confidence"]
                blocks_for_image = ocr_result.get("blocks", [])
                extracted = extract_compliance_fields(raw_ocr_text, validated_ocr_text)

            all_extracted.append(extracted)
            all_ocr_confidences.append(ocr_confidence)
            all_raw_texts.append(raw_ocr_text)
            all_blocks.append(blocks_for_image)

            product_images_records.append({
                "id": pos_idx + 1,
                "view": view_label,
                "path": orig_url,
                "image_path": orig_url,
                "crop_path": crop_url,
                "cropped_path": crop_url,
                "cropped_image_path": crop_url,
                "quality_score": round(quality_results[orig_idx]["quality_score"], 1),
                "ocr_confidence": round(ocr_confidence, 3),
            })

        if not all_extracted:
            raise ValueError("No images could be processed through the inspection pipeline.")

        # -----------------------------------------------------------------------
        # Phase 3c — 360° Panorama Stitching (Optional / Mode-based)
        # -----------------------------------------------------------------------
        panorama_data = None
        if inspection_mode == "panorama" or len(accepted_indices) >= 2:
            accepted_bgrs = [decoded_bgr_list[i] for i in accepted_indices]
            try:
                stitch_res = stitch_package_images(
                    images_bgr=accepted_bgrs,
                    storage_dir=STORAGE_DIR,
                    inspection_id=inspection.id,
                )
                panorama_data = {
                    "status": stitch_res["status"],
                    "panorama_path": stitch_res.get("panorama_path"),
                    "overlap_confidence": stitch_res.get("overlap_confidence", 0.0),
                    "message": stitch_res.get("message", ""),
                    "fallback_reason": stitch_res.get("fallback_reason"),
                }
                if stitch_res["status"] == "success":
                    logger.info(f"360° Panorama unwrap generated: {stitch_res['panorama_path']}")
            except Exception as e:
                logger.warning(f"Panorama stitching exception: {e}")
                panorama_data = {
                    "status": "fallback",
                    "panorama_path": None,
                    "overlap_confidence": 0.0,
                    "message": "Panorama could not be generated due to insufficient overlap. Multi-image inspection continued.",
                    "fallback_reason": "EXCEPTION",
                }

        # -----------------------------------------------------------------------
        # Phase 4 — Multi-view deduplication & evidence fusion
        # -----------------------------------------------------------------------
        merged_extracted = merge_multi_image_fields(
            all_extracted=all_extracted,
            all_ocr_confidences=all_ocr_confidences,
            views=[p["view"] for p in product_images_records],
            image_paths=[p["path"] for p in product_images_records],
            all_blocks=all_blocks,
        )

        merged_extracted["_ai_engine"] = ai_engine_label
        if "gemini_analysis" in best_quality_result:
            merged_extracted["_gemini_analysis"] = best_quality_result["gemini_analysis"]

        combined_raw_text = "\n\n--- IMAGE BOUNDARY ---\n\n".join(all_raw_texts)
        final_ocr_confidence = max(all_ocr_confidences) if all_ocr_confidences else 0.0

        # -----------------------------------------------------------------------
        # Phase 5 — Product Intelligence Engine (Secondary Analysis)
        # -----------------------------------------------------------------------
        product_intelligence = analyze_product_intelligence(
            combined_ocr_text=combined_raw_text,
            gemini_service=gemini_svc if use_gemini else None,
            image_bytes_list=[image_bytes_list[i] for i in accepted_indices],
        )

        # -----------------------------------------------------------------------
        # Phase 6 — Legal Metrology Rule Engine Evaluation
        # -----------------------------------------------------------------------
        rule_input = {k: v for k, v in merged_extracted.items() if not k.startswith("_")}
        score, overall_status, rule_results = evaluate_compliance(
            extracted_data=rule_input,
            is_food_product=is_food_product,
        )

        # -----------------------------------------------------------------------
        # Phase 7 — Persist inspection record & evidence violations
        # -----------------------------------------------------------------------
        inspection.image_path = first_orig_url
        inspection.cropped_image_path = first_crop_url
        inspection.raw_ocr_text = combined_raw_text
        inspection.validated_ocr_text = combined_raw_text
        inspection.ocr_confidence = final_ocr_confidence
        inspection.ocr_retry_count = len(accepted_indices)
        inspection.extracted_data = merged_extracted
        inspection.compliance_score = score
        inspection.overall_status = overall_status
        inspection.inspection_mode = inspection_mode
        inspection.product_images = product_images_records
        inspection.panorama_data = panorama_data
        inspection.product_intelligence = product_intelligence

        for res in rule_results:
            violation = Violation(
                inspection_id=inspection.id,
                rule_code=res["rule_code"],
                description=res["description"],
                severity=res["severity"],
                status=res["status"],
                source_view=res.get("source_view") or "Front",
                evidence_image_path=res.get("evidence_image_path") or first_orig_url,
                bounding_box=res.get("bounding_box"),
                detected_value=res.get("detected_value"),
                expected_condition=res.get("expected_condition"),
                confidence=float(res.get("confidence") or 0.0),
            )
            db.add(violation)

        db.commit()
        db.refresh(inspection)

        logger.info(
            f"Inspection #{inspection.id} complete — "
            f"mode={inspection_mode}, images={len(accepted_indices)}, "
            f"score={score:.1f}, status={overall_status}"
        )
        return inspection

    except Exception as e:
        db.rollback()
        logger.error(f"Inspection pipeline failure for #{inspection.id}: {e}", exc_info=True)
        inspection.overall_status = "Non-Compliant"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspection pipeline error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Video Inspection Endpoint
# ---------------------------------------------------------------------------

@router.post("/video", response_model=InspectionResponse)
async def upload_and_inspect_video(
    video: UploadFile = File(..., description="Continuous packaging recording (.mp4, .webm, .mov)"),
    product_name: str = Form("Packaged Commodity"),
    brand: str = Form("Generic Brand"),
    is_food_product: bool = Form(True),
    ai_engine: str = Form("gemini", description="Vision engine: 'gemini' | 'hybrid' | 'local'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Video-Based Package Inspection Pipeline:
    1. Stream Ingestion & intelligent temporal sampling (1–2 fps)
    2. Quality Gate: Discards motion-blur and glare frames via Laplacian variance
    3. Perceptual Deduplication: Removes near-identical duplicate angles
    4. View Coverage: Classifies frames into FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM
    5. Keyframe Extraction & Multi-View OCR Fusion
    6. Legal Metrology Compliance Audit + Product Intelligence
    """
    if current_user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers have read-only access and are not authorized to inspect products.",
        )

    # Write video to temporary file
    suffix = os.path.splitext(video.filename or ".mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_vid:
        content = await video.read()
        temp_vid.write(content)
        temp_video_path = temp_vid.name

    inspection = Inspection(
        inspector_id=current_user.id,
        product_name=product_name.strip() or "Packaged Commodity",
        brand=brand.strip() or "Generic Brand",
        image_path="",
        inspection_mode="video",
        quality_score=80.0,
        compliance_score=0.0,
        overall_status="Processing",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    try:
        # 1. Video Processing & Keyframe Extraction
        video_result = process_inspection_video(
            video_path=temp_video_path,
            storage_dir=STORAGE_DIR,
            inspection_id=inspection.id,
            max_keyframes=8,
        )
        keyframes = video_result["keyframes"]
        telemetry = video_result["telemetry"]

        if not keyframes:
            raise ValueError("No viable inspection frames could be extracted from the video.")

        # 2. Run OCR & Extraction on Keyframes
        all_extracted = []
        all_ocr_confidences = []
        all_raw_texts = []
        all_blocks = []
        product_images_records = []

        first_orig_url = keyframes[0]["path"]
        first_crop_url = keyframes[0]["path"]

        gemini_svc = get_gemini_service()
        use_gemini = (ai_engine.lower() in ("gemini", "hybrid")) and gemini_svc.is_configured
        ai_engine_label = (
            "Gemini Multimodal Vision AI"
            if ai_engine.lower() == "gemini" and use_gemini
            else ("Hybrid AI Consensus" if ai_engine.lower() == "hybrid" and use_gemini else "Local OpenCV + EasyOCR")
        )

        for k_idx, kf in enumerate(keyframes):
            # Encode frame to bytes for pipeline
            _, buf = cv2.imencode(".png", kf["bgr"])
            kf_bytes = buf.tobytes()

            orig_fn, crop_fn, _, variants = process_label_image(
                image_bytes=kf_bytes,
                storage_dir=STORAGE_DIR,
                inspection_id=inspection.id,
                image_index=k_idx,
            )

            crop_bgr_path = os.path.join(STORAGE_DIR, crop_fn)
            cropped_bgr = cv2.imread(crop_bgr_path) if os.path.exists(crop_bgr_path) else kf["bgr"]

            ocr_res = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
            raw_text = ocr_res["raw_ocr_text"]
            validated_text = ocr_res["validated_ocr_text"]
            conf = ocr_res["ocr_confidence"]
            blocks = ocr_res.get("blocks", [])

            if ai_engine.lower() in ("gemini", "hybrid") and use_gemini:
                try:
                    g_res = gemini_svc.extract_statutory_fields(kf_bytes, is_food_product=is_food_product)
                    if g_res.get("success"):
                        extracted = g_res.get("fields", {})
                        raw_text = g_res.get("verbatim_text", raw_text)
                        conf = max(conf, g_res.get("confidence", 0.90))
                    else:
                        extracted = extract_compliance_fields(raw_text, validated_text)
                except Exception:
                    extracted = extract_compliance_fields(raw_text, validated_text)
            else:
                extracted = extract_compliance_fields(raw_text, validated_text)

            all_extracted.append(extracted)
            all_ocr_confidences.append(conf)
            all_raw_texts.append(raw_text)
            all_blocks.append(blocks)

            product_images_records.append({
                "id": k_idx + 1,
                "view": f"{kf['view']} (Video Frame #{kf['frame_index']})",
                "path": f"/storage/images/{orig_fn}",
                "image_path": f"/storage/images/{orig_fn}",
                "crop_path": f"/storage/images/{crop_fn}",
                "cropped_path": f"/storage/images/{crop_fn}",
                "cropped_image_path": f"/storage/images/{crop_fn}",
                "quality_score": kf["quality_score"],
                "ocr_confidence": conf,
            })

        # 3. Fuse Keyframe Declarations
        merged_extracted = merge_multi_image_fields(
            all_extracted=all_extracted,
            all_ocr_confidences=all_ocr_confidences,
            views=[p["view"] for p in product_images_records],
            image_paths=[p["path"] for p in product_images_records],
            all_blocks=all_blocks,
        )
        merged_extracted["_ai_engine"] = ai_engine_label
        combined_raw_text = "\n\n--- VIDEO KEYFRAME BOUNDARY ---\n\n".join(all_raw_texts)

        # 4. Product Intelligence
        product_intelligence = analyze_product_intelligence(combined_raw_text)

        # 5. Rule Engine
        rule_input = {k: v for k, v in merged_extracted.items() if not k.startswith("_")}
        score, overall_status, rule_results = evaluate_compliance(
            extracted_data=rule_input,
            is_food_product=is_food_product,
        )

        # 6. Save Record
        inspection.image_path = first_orig_url
        inspection.cropped_image_path = first_crop_url
        inspection.raw_ocr_text = combined_raw_text
        inspection.validated_ocr_text = combined_raw_text
        inspection.ocr_confidence = max(all_ocr_confidences) if all_ocr_confidences else 0.0
        inspection.ocr_retry_count = len(keyframes)
        inspection.extracted_data = merged_extracted
        inspection.compliance_score = score
        inspection.overall_status = overall_status
        inspection.inspection_mode = "video"
        inspection.product_images = product_images_records
        inspection.video_metadata = telemetry
        inspection.product_intelligence = product_intelligence

        for res in rule_results:
            violation = Violation(
                inspection_id=inspection.id,
                rule_code=res["rule_code"],
                description=res["description"],
                severity=res["severity"],
                status=res["status"],
                source_view=res.get("source_view") or "Video View",
                evidence_image_path=res.get("evidence_image_path") or first_orig_url,
                bounding_box=res.get("bounding_box"),
                detected_value=res.get("detected_value"),
                expected_condition=res.get("expected_condition"),
                confidence=float(res.get("confidence") or 0.0),
            )
            db.add(violation)

        db.commit()
        db.refresh(inspection)
        return inspection

    finally:
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Dedicated Panorama Inspection Endpoint
# ---------------------------------------------------------------------------

@router.post("/panorama", response_model=InspectionResponse)
async def upload_and_inspect_panorama(
    images: List[UploadFile] = File(..., description="Overlapping package photos for 360° unwrap"),
    product_name: str = Form("Packaged Commodity"),
    brand: str = Form("Generic Brand"),
    is_food_product: bool = Form(True),
    ai_engine: str = Form("gemini"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    360° Package Panorama Inspection:
    Stitches overlapping packaging images into an unwrapped planar panorama.
    If overlap is insufficient, automatically falls back to multi-image inspection.
    """
    return await upload_and_inspect(
        images=images,
        image=None,
        views=None,
        inspection_mode="panorama",
        product_name=product_name,
        brand=brand,
        is_food_product=is_food_product,
        ai_engine=ai_engine,
        current_user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Product Intelligence Endpoint
# ---------------------------------------------------------------------------

@router.get("/{inspection_id}/product-intelligence")
def get_product_intelligence(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve structured ingredient, additive, and allergen analysis for an inspection."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection.product_intelligence or {}


# ---------------------------------------------------------------------------
@router.get("/inspectors", response_model=List[InspectorOption])
def get_inspectors_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all inspectors and admins for filtering dropdowns."""
    users = db.query(User).filter(User.role.in_(["inspector", "admin"])).all()
    return [
        InspectorOption(id=u.id, name=u.name, email=u.email, role=u.role)
        for u in users
    ]


@router.get("", response_model=List[InspectionSummary])
def list_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    inspector_id: Optional[int] = Query(None, description="Optional inspector ID filter for admin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past inspections with pagination, role-scoping, and optional status/inspector filters."""
    query = db.query(Inspection)

    if current_user.role == "inspector":
        # Inspector is strictly scoped to their own inspections
        query = query.filter(Inspection.inspector_id == current_user.id)
    elif current_user.role == "admin":
        if inspector_id is not None:
            query = query.filter(Inspection.inspector_id == inspector_id)
    # Viewer sees all inspections across the organization

    if status_filter:
        query = query.filter(Inspection.overall_status == status_filter)

    inspections = query.order_by(Inspection.created_at.desc()).offset(skip).limit(limit).all()

    summaries = []
    for insp in inspections:
        summaries.append(
            InspectionSummary(
                id=insp.id,
                product_name=insp.product_name,
                brand=insp.brand,
                compliance_score=insp.compliance_score,
                quality_score=insp.quality_score or 0.0,
                ocr_confidence=insp.ocr_confidence or 0.0,
                overall_status=insp.overall_status,
                created_at=insp.created_at,
                inspector_name=insp.inspector.name if insp.inspector else "Unknown Inspector",
                image_path=insp.image_path or "/storage/images/placeholder.png",
            )
        )
    return summaries


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of an inspection by ID."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection


@router.get("/{inspection_id}/report.pdf")
def download_pdf_report(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    """Generate and stream official compliance inspection PDF report."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    violations_data = [
        {
            "rule_code": v.rule_code,
            "description": v.description,
            "severity": v.severity,
            "status": v.status,
            "source_view": getattr(v, "source_view", None),
            "evidence_image_path": getattr(v, "evidence_image_path", None),
            "detected_value": getattr(v, "detected_value", None),
            "expected_condition": getattr(v, "expected_condition", None),
            "confidence": getattr(v, "confidence", None),
            "bounding_box": getattr(v, "bounding_box", None),
        }
        for v in inspection.violations
    ]

    inspector_name = inspection.inspector.name if inspection.inspector else "Legal Metrology Officer"

    pdf_bytes = generate_inspection_pdf(
        inspection_id=inspection.id,
        created_at=inspection.created_at,
        product_name=inspection.product_name,
        brand=inspection.brand,
        overall_status=inspection.overall_status,
        compliance_score=inspection.compliance_score,
        violations=violations_data,
        extracted_data=inspection.extracted_data or {},
        inspector_name=inspector_name,
        location="Directorate of Legal Metrology, Enforcement Wing",
        quality_score=inspection.quality_score or 0.0,
        ocr_confidence=inspection.ocr_confidence or 0.0,
        ocr_retry_count=inspection.ocr_retry_count or 0,
        inspection_mode=inspection.inspection_mode or "multi_image",
        product_images=inspection.product_images,
        product_intelligence=inspection.product_intelligence,
        video_metadata=inspection.video_metadata,
        panorama_data=inspection.panorama_data,
    )

    filename = f"legal_metrology_report_{inspection.id}_{inspection.brand.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
