import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import Inspection, Violation, User
from app.schemas.schemas import InspectionResponse, InspectionSummary
from app.auth.dependencies import get_current_user
from app.cv_pipeline.preprocessor import process_label_image
from app.ocr.ocr_service import perform_ocr
from app.extraction.extractor import extract_compliance_fields
from app.rule_engine.rules import evaluate_compliance
from app.reports.pdf_generator import generate_inspection_pdf

router = APIRouter(prefix="/inspections", tags=["Inspections"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "images"))


@router.post("/upload", response_model=InspectionResponse)
async def upload_and_inspect(
    image: UploadFile = File(...),
    product_name: str = Form("Packaged Commodity"),
    brand: str = Form("Generic Brand"),
    is_food_product: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Full pipeline endpoint:
    1. Ingest image upload
    2. OpenCV preprocessing, deskewing, contour-based label crop
    3. EasyOCR with pytesseract fallback
    4. Regex-based Legal Metrology field extraction
    5. Rule Engine evaluation against Rules, 2011
    6. Persist inspection & violations in database
    7. Return full compliance report
    """
    # Validate content type
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image (PNG, JPEG, etc.).",
        )

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file received.",
        )

    # Pre-create inspection record to obtain auto-increment ID
    inspection = Inspection(
        inspector_id=current_user.id,
        product_name=product_name.strip() or "Packaged Commodity",
        brand=brand.strip() or "Generic Brand",
        image_path="",
        compliance_score=0.0,
        overall_status="Processing",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    try:
        # 1 & 2: OpenCV Pipeline
        orig_filename, crop_filename, enhanced_gray = process_label_image(
            image_bytes=image_bytes,
            storage_dir=STORAGE_DIR,
            inspection_id=inspection.id,
        )

        orig_url = f"/storage/images/{orig_filename}"
        crop_url = f"/storage/images/{crop_filename}"

        # 3: OCR Pipeline
        raw_ocr_text, avg_conf, blocks = perform_ocr(enhanced_gray)

        # 4: Extraction Pipeline
        extracted_data = extract_compliance_fields(raw_ocr_text)

        # 5: Rule Engine
        score, overall_status, rule_results = evaluate_compliance(
            extracted_data=extracted_data,
            is_food_product=is_food_product,
        )

        # Update Inspection Record
        inspection.image_path = orig_url
        inspection.cropped_image_path = crop_url
        inspection.raw_ocr_text = raw_ocr_text
        inspection.extracted_data = extracted_data
        inspection.compliance_score = score
        inspection.overall_status = overall_status

        # Create Violation / Rule Checklist Records
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
        return inspection

    except Exception as e:
        db.rollback()
        # Mark as failed if processing exception occurred
        inspection.overall_status = "Non-Compliant"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspection pipeline error: {str(e)}",
        )


@router.get("", response_model=List[InspectionSummary])
def list_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past inspections with pagination and optional status filter."""
    query = db.query(Inspection)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )
    return inspection


@router.get("/{inspection_id}/report.pdf")
def download_pdf_report(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    """Generate and stream official compliance inspection PDF report."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

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
    )

    filename = f"legal_metrology_report_{inspection.id}_{inspection.brand.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
