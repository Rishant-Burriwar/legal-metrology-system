import os
import logging
import cv2
import numpy as np
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import Inspection, Violation, User
from app.schemas.schemas import InspectionResponse, InspectionSummary, InspectorOption
from app.auth.dependencies import get_current_user
from app.cv_pipeline.quality_assessor import assess_image_quality
from app.cv_pipeline.preprocessor import process_label_image
from app.ocr.ocr_service import perform_adaptive_ocr_pipeline
from app.extraction.extractor import extract_compliance_fields, merge_multi_image_fields
from app.rule_engine.rules import evaluate_compliance
from app.reports.pdf_generator import generate_inspection_pdf
from app.services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspections", tags=["Inspections"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "images"))
MAX_IMAGES = 5


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
    images: Optional[List[UploadFile]] = File(None, description="1–5 label photos of the same product"),
    image: Optional[UploadFile] = File(None, description="Single label photo (backward compatibility)"),
    product_name: str = Form("Packaged Commodity"),
    brand: str = Form("Generic Brand"),
    is_food_product: bool = Form(True),
    ai_engine: str = Form("gemini", description="Vision engine: 'gemini' | 'hybrid' | 'local'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Full multi-image inspection pipeline with Gemini Multimodal AI:

    Accepts up to 5 photos of the same product label (different faces/angles).
    For each acceptable image:
      1. Pre-OCR Quality Gate (blur, brightness, resolution, contrast)
      2. Gemini Multimodal Visual Packaging Analysis (surface, glare, curvature, legibility)
      3. OpenCV Preprocessing — 8 variants (A–H) & contour cropping
      4. Text & Statutory Field Extraction (Gemini AI, Hybrid Consensus, or Local OCR)
      5. Rule Engine evaluation against Legal Metrology Rules, 2011 (LM-01..LM-07)
    Final step: merge fields across all images, persist audit trail and return report.
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

        if qr["is_acceptable"]:
            accepted_indices.append(len(image_bytes_list) - 1)
        else:
            logger.warning(
                f"Image #{idx + 1} failed quality gate: {qr['rejection_reasons']}"
            )

    # If NO image passed quality gate, return a rich rejection error
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

    # Use best quality score for the inspection record
    best_quality_score = max(
        quality_results[i]["quality_score"] for i in accepted_indices
    )
    best_quality_result = dict(
        max(
            (quality_results[i] for i in accepted_indices),
            key=lambda q: q["quality_score"],
        )
    )

    # Run Gemini Multimodal packaging visual analysis if enabled
    if use_gemini and accepted_indices:
        try:
            primary_img_bytes = image_bytes_list[accepted_indices[0]]
            gemini_vis = gemini_svc.analyze_packaging_image(primary_img_bytes)
            best_quality_result["gemini_analysis"] = gemini_vis
            logger.info(f"Gemini visual analysis complete: {gemini_vis.get('packaging_type')}, legibility={gemini_vis.get('legibility_score')}")
        except Exception as e:
            logger.warning(f"Gemini visual analysis failed: {e}")

    # -----------------------------------------------------------------------
    # Phase 2 — Create inspection record (accepted at least one image)
    # -----------------------------------------------------------------------
    inspection = Inspection(
        inspector_id=current_user.id,
        product_name=product_name.strip() or "Packaged Commodity",
        brand=brand.strip() or "Generic Brand",
        image_path="",
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
        # Phase 3 — Per-image: preprocess → OCR/Gemini → extract fields
        # -----------------------------------------------------------------------
        all_extracted: List[dict] = []
        all_ocr_confidences: List[float] = []
        all_raw_texts: List[str] = []

        first_orig_url = ""
        first_crop_url = ""

        for list_idx, img_bytes in enumerate(image_bytes_list):
            if list_idx not in accepted_indices:
                continue

            logger.info(
                f"Inspection #{inspection.id}: Processing image {list_idx + 1}/{len(image_bytes_list)} (Engine: {ai_engine_label})"
            )

            # 3a. OpenCV preprocessing — returns 8 variants
            orig_fn, crop_fn, enhanced_gray, variants = process_label_image(
                image_bytes=img_bytes,
                storage_dir=STORAGE_DIR,
                inspection_id=inspection.id,
                image_index=list_idx,
            )

            if not first_orig_url:
                first_orig_url = f"/storage/images/{orig_fn}"
                first_crop_url = f"/storage/images/{crop_fn}"

            # Decode cropped BGR for YOLO region detection or local fallback
            crop_bgr_path = os.path.join(STORAGE_DIR, crop_fn)
            cropped_bgr = cv2.imread(crop_bgr_path) if os.path.exists(crop_bgr_path) else None

            # 3b. Extraction according to selected AI Engine
            if ai_engine.lower() == "gemini" and use_gemini:
                logger.info(f"Running Gemini Multimodal Vision extraction for image #{list_idx + 1}...")
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
                    extracted = extract_compliance_fields(raw_ocr_text, validated_ocr_text)

            elif ai_engine.lower() == "hybrid" and use_gemini:
                logger.info(f"Running Hybrid Consensus (Gemini + EasyOCR) for image #{list_idx + 1}...")
                ocr_result = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
                local_extracted = extract_compliance_fields(ocr_result["raw_ocr_text"], ocr_result["validated_ocr_text"])

                g_res = gemini_svc.extract_statutory_fields(img_bytes, is_food_product=is_food_product)
                g_fields = g_res.get("fields", {}) if g_res.get("success") else {}
                g_text = g_res.get("verbatim_text", "")

                extracted = gemini_svc.hybrid_consensus_merge(
                    gemini_fields=g_fields,
                    local_ocr_fields=local_extracted,
                    gemini_conf=g_res.get("confidence", 0.95),
                    local_conf=ocr_result["ocr_confidence"],
                )
                raw_ocr_text = f"=== GEMINI VISION TRANSCRIPT ===\n{g_text}\n\n=== LOCAL OCR TRANSCRIPT ===\n{ocr_result['raw_ocr_text']}"
                validated_ocr_text = raw_ocr_text
                ocr_confidence = max(g_res.get("confidence", 0.95), ocr_result["ocr_confidence"])

            else:
                # Local offline pipeline (OpenCV + EasyOCR + Tesseract)
                ocr_result = perform_adaptive_ocr_pipeline(variants=variants, cropped_bgr=cropped_bgr)
                raw_ocr_text = ocr_result["raw_ocr_text"]
                validated_ocr_text = ocr_result["validated_ocr_text"]
                ocr_confidence = ocr_result["ocr_confidence"]
                extracted = extract_compliance_fields(raw_ocr_text, validated_ocr_text)

            logger.info(
                f"  Image {list_idx + 1}: conf={ocr_confidence:.3f}, text_len={len(raw_ocr_text)}"
            )

            all_extracted.append(extracted)
            all_ocr_confidences.append(ocr_confidence)
            all_raw_texts.append(raw_ocr_text)

        if not all_extracted:
            raise ValueError("No images could be processed through the inspection pipeline.")

        # -----------------------------------------------------------------------
        # Phase 4 — Merge fields across all images
        # -----------------------------------------------------------------------
        merged_extracted = merge_multi_image_fields(
            all_extracted=all_extracted,
            all_ocr_confidences=all_ocr_confidences,
        )

        merged_extracted["_ai_engine"] = ai_engine_label
        if "gemini_analysis" in best_quality_result:
            merged_extracted["_gemini_analysis"] = best_quality_result["gemini_analysis"]

        # Combine all raw OCR text for audit trail (separated by image marker)
        combined_raw_text = "\n\n--- IMAGE BOUNDARY ---\n\n".join(all_raw_texts)
        final_ocr_confidence = max(all_ocr_confidences)
        total_retry_count = sum(
            ocr_result.get("ocr_retry_count", 0)
            for ocr_result in [{"ocr_retry_count": 0}]  # placeholder
        )

        # -----------------------------------------------------------------------
        # Phase 5 — Rule Engine evaluation
        # -----------------------------------------------------------------------
        # Strip internal metadata before passing to rule engine
        rule_input = {k: v for k, v in merged_extracted.items() if not k.startswith("_")}
        score, overall_status, rule_results = evaluate_compliance(
            extracted_data=rule_input,
            is_food_product=is_food_product,
        )

        # -----------------------------------------------------------------------
        # Phase 6 — Persist inspection record
        # -----------------------------------------------------------------------
        inspection.image_path = first_orig_url
        inspection.cropped_image_path = first_crop_url
        inspection.raw_ocr_text = combined_raw_text
        inspection.validated_ocr_text = combined_raw_text  # merged text
        inspection.ocr_confidence = final_ocr_confidence
        inspection.ocr_retry_count = len(accepted_indices)  # images processed
        inspection.extracted_data = merged_extracted
        inspection.compliance_score = score
        inspection.overall_status = overall_status

        for res in rule_results:
            violation = Violation(
                inspection_id=inspection.id,
                rule_code=res["rule_code"],
                description=res["description"],
                severity=res["severity"],
                status=res["status"],
            )
            db.add(violation)

        db.commit()
        db.refresh(inspection)

        logger.info(
            f"Inspection #{inspection.id} complete — "
            f"images_accepted={len(accepted_indices)}/{len(upload_list)}, "
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
    )

    filename = f"legal_metrology_report_{inspection.id}_{inspection.brand.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
