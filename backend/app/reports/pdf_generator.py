"""
Statutory PDF Inspection Report Generator — Directorate of Legal Metrology
==========================================================================

Generates official 7-Section Statutory Inspection Orders:
  Section 1: Inspection Identification & Metadata
  Section 2: Input Packaging Evidence (Multi-View Facets, Video Telemetry, Panorama)
  Section 3: Mandatory Statutory Declarations (LM-01..LM-07) with Facet Attribution
  Section 4: Statutory Compliance Verdict & Score
  Section 5: Evidentiary Violations Table (Rule, Detected Value, Expected Rule, Evidence)
  Section 6: Product Intelligence (Ingredients, Decoded Additives with INS Codes, Allergens)
  Section 7: Statutory Enforcement Notice, Legal Disclaimer & Digital Seal
"""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_inspection_pdf(
    inspection_id: int,
    created_at: datetime,
    product_name: str,
    brand: str,
    overall_status: str,
    compliance_score: float,
    violations: List[Dict[str, Any]],
    extracted_data: Dict[str, Any],
    inspector_name: str = "Senior Inspector Sharma",
    location: str = "New Delhi Central Verification Zone",
    quality_score: float = 0.0,
    ocr_confidence: float = 0.0,
    ocr_retry_count: int = 0,
    inspection_mode: str = "multi_image",
    product_images: Optional[List[Dict[str, Any]]] = None,
    product_intelligence: Optional[Dict[str, Any]] = None,
    video_metadata: Optional[Dict[str, Any]] = None,
    panorama_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=32,
        bottomMargin=32,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
    )
    cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
    )
    cell_badge_pass = ParagraphStyle(
        "CellBadgePass",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#166534"),
    )
    cell_badge_fail = ParagraphStyle(
        "CellBadgeFail",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#991b1b"),
    )

    story = []

    # Header
    story.append(Paragraph("DIRECTORATE OF LEGAL METROLOGY", subtitle_style))
    story.append(Paragraph("GOVERNMENT OF INDIA • DEPARTMENT OF CONSUMER AFFAIRS", subtitle_style))
    story.append(Paragraph("STATUTORY PACKAGING COMPLIANCE INSPECTION REPORT", title_style))
    story.append(Paragraph("Enforcement Order under Legal Metrology (Packaged Commodities) Rules, 2011", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

    # =========================================================================
    # SECTION 1 — INSPECTION INFORMATION
    # =========================================================================
    story.append(Paragraph("SECTION 1 — INSPECTION IDENTIFICATION & METADATA", section_heading))

    status_text_color = "#166534" if overall_status == "Compliant" else "#991b1b"
    status_html = f"<font color='{status_text_color}'><b>{overall_status.upper()} ({compliance_score}%)</b></font>"

    date_str = created_at.strftime("%d-%b-%Y %H:%M UTC") if isinstance(created_at, datetime) else str(created_at)
    mode_label = (
        "360° Video Stream Ingestion"
        if inspection_mode == "video"
        else ("360° Cylindrical Panorama Unwrap" if inspection_mode == "panorama" else "Multi-Angle Packaging Facets")
    )

    meta_data = [
        [
            Paragraph("<b>Inspection Record ID:</b>", cell_style),
            Paragraph(f"LM-{inspection_id:05d}", cell_bold),
            Paragraph("<b>Inspection Date:</b>", cell_style),
            Paragraph(date_str, cell_style),
        ],
        [
            Paragraph("<b>Product Commodity:</b>", cell_style),
            Paragraph(product_name, cell_bold),
            Paragraph("<b>Brand / Entity:</b>", cell_style),
            Paragraph(brand, cell_style),
        ],
        [
            Paragraph("<b>Inspecting Authority:</b>", cell_style),
            Paragraph(inspector_name, cell_style),
            Paragraph("<b>Enforcement Zone:</b>", cell_style),
            Paragraph(location, cell_style),
        ],
        [
            Paragraph("<b>Inspection Mode:</b>", cell_style),
            Paragraph(mode_label, cell_bold),
            Paragraph("<b>AI Vision Engine:</b>", cell_style),
            Paragraph(str(extracted_data.get("_ai_engine", "Gemini Multimodal Vision AI")), cell_style),
        ],
        [
            Paragraph("<b>Packaging Quality Score:</b>", cell_style),
            Paragraph(f"{quality_score:.1f} / 100", cell_style),
            Paragraph("<b>Statutory Verdict:</b>", cell_style),
            Paragraph(status_html, cell_bold),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[120, 150, 120, 150])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 2 — INPUT EVIDENCE & TELEMETRY
    # =========================================================================
    story.append(Paragraph("SECTION 2 — INPUT PACKAGING EVIDENCE & TELEMETRY", section_heading))

    evidence_rows = [
        [
            Paragraph("<b>Evidence Source</b>", cell_bold),
            Paragraph("<b>Facet / Angle Name</b>", cell_bold),
            Paragraph("<b>Quality Index</b>", cell_bold),
            Paragraph("<b>Telemetry Notes</b>", cell_bold),
        ]
    ]

    if product_images:
        for p in product_images:
            evidence_rows.append([
                Paragraph(f"Facet #{p.get('id', 1)}", cell_style),
                Paragraph(str(p.get("view", "Angle")), cell_bold),
                Paragraph(f"{p.get('quality_score', 0):.1f}%", cell_style),
                Paragraph(f"OCR Conf: {int((p.get('ocr_confidence', 0) or 0) * 100)}%", cell_style),
            ])
    elif video_metadata:
        evidence_rows.append([
            Paragraph("Video Recording", cell_style),
            Paragraph(f"{video_metadata.get('useful_views_detected', 0)} Viewpoints", cell_bold),
            Paragraph("Automated Filtered", cell_style),
            Paragraph(
                f"Captured: {video_metadata.get('frames_captured', 0)} frames | "
                f"Analyzed: {video_metadata.get('frames_analyzed', 0)} keyframes | "
                f"Filtered: {video_metadata.get('frames_discarded', 0)} blurry/dup",
                cell_style,
            ),
        ])
    else:
        evidence_rows.append([
            Paragraph("Primary Label", cell_style),
            Paragraph("Principal Display Panel", cell_bold),
            Paragraph(f"{quality_score:.1f}%", cell_style),
            Paragraph("Direct Photographic Ingest", cell_style),
        ])

    if panorama_data:
        p_status = "Successfully Assembled" if panorama_data.get("status") == "success" else "Fallback to Multi-Image"
        evidence_rows.append([
            Paragraph("360° Panorama", cell_style),
            Paragraph(f"Unwrap ({p_status})", cell_bold),
            Paragraph(f"{int(panorama_data.get('overlap_confidence', 0) * 100)}% Overlap", cell_style),
            Paragraph(str(panorama_data.get("message", "Processed")), cell_style),
        ])

    ev_table = Table(evidence_rows, colWidths=[100, 130, 90, 220])
    ev_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ])
    )
    story.append(ev_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 3 — EXTRACTED STATUTORY DECLARATIONS
    # =========================================================================
    story.append(Paragraph("SECTION 3 — EXTRACTED STATUTORY DECLARATIONS (RULE 6)", section_heading))

    field_defs = [
        ("mrp", "Maximum Retail Price (MRP)", "Rule 6(1)(e)"),
        ("net_quantity", "Net Quantity", "Rule 6(1)(b)"),
        ("manufacture_date", "Date of Mfg / Packing", "Rule 6(1)(d)"),
        ("customer_care", "Consumer Care Contacts", "Rule 6(1)(n)"),
        ("manufacturer_details", "Manufacturer / Packer", "Rule 6(1)(a)"),
        ("fssai_license", "FSSAI License Number", "Rule LM-06"),
        ("country_of_origin", "Country of Origin", "Rule 6(1)(m)"),
    ]

    decl_rows = [
        [
            Paragraph("<b>Statutory Field</b>", cell_bold),
            Paragraph("<b>Mandatory Provision</b>", cell_bold),
            Paragraph("<b>Detected Value</b>", cell_bold),
            Paragraph("<b>Source Facet</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
        ]
    ]

    for key, label, prov in field_defs:
        f = extracted_data.get(key, {})
        val = f.get("value") or "Not Detected"
        status_raw = f.get("status", "not_found")
        source_v = f.get("source_view") or "Front"
        status_disp = status_raw.replace("_", " ").title()

        st_color = "#16a34a" if status_raw == "found" else ("#d97706" if status_raw == "low_confidence" else "#dc2626")

        decl_rows.append([
            Paragraph(label, cell_style),
            Paragraph(prov, cell_style),
            Paragraph(str(val)[:80], cell_style),
            Paragraph(source_v, cell_style),
            Paragraph(f"<font color='{st_color}'><b>{status_disp}</b></font>", cell_style),
        ])

    decl_table = Table(decl_rows, colWidths=[120, 90, 180, 75, 75])
    decl_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ])
    )
    story.append(decl_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 4 & 5 — STATUTORY VIOLATIONS & VISUAL EVIDENCE
    # =========================================================================
    story.append(Paragraph("SECTION 4 & 5 — STATUTORY VIOLATIONS & EVIDENTIARY AUDIT", section_heading))

    viol_rows = [
        [
            Paragraph("<b>Rule</b>", cell_bold),
            Paragraph("<b>Requirement Description</b>", cell_bold),
            Paragraph("<b>Detected / Expected</b>", cell_bold),
            Paragraph("<b>Severity</b>", cell_bold),
            Paragraph("<b>Verdict</b>", cell_bold),
            Paragraph("<b>Evidence Facet</b>", cell_bold),
        ]
    ]

    for v in violations:
        st = v.get("status", "Fail")
        st_style = cell_badge_pass if st == "Pass" else cell_badge_fail
        sev_color = "#991b1b" if v.get("severity") == "Major" else "#d97706"
        det = v.get("detected_value") or "Missing"
        exp = v.get("expected_condition") or "Statutory requirement"
        det_exp = f"Detected: {det[:35]}<br/>Expected: {exp[:35]}"

        viol_rows.append([
            Paragraph(f"<b>{v.get('rule_code', '')}</b>", cell_style),
            Paragraph(v.get("description", ""), cell_style),
            Paragraph(det_exp, cell_style),
            Paragraph(f"<font color='{sev_color}'><b>{v.get('severity', '')}</b></font>", cell_style),
            Paragraph(f"<b>{st}</b>", st_style),
            Paragraph(str(v.get("source_view") or "Front"), cell_style),
        ])

    viol_table = Table(viol_rows, colWidths=[45, 150, 160, 50, 50, 85])
    viol_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ])
    )
    story.append(viol_table)
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 6 — PRODUCT INTELLIGENCE & COMPOSITION
    # =========================================================================
    story.append(Paragraph("SECTION 6 — PRODUCT COMPOSITION & ADDITIVE INTELLIGENCE", section_heading))

    pi = product_intelligence or {}
    additives = pi.get("additives", [])
    allergens = pi.get("allergens", [])
    ingredients = pi.get("ingredients", [])

    pi_summary_text = (
        f"<b>Ingredients Audited:</b> {len(ingredients)} detected | "
        f"<b>Declared Additives:</b> {len(additives)} decoded | "
        f"<b>Allergens Identified:</b> {len(allergens)} flagged | "
        f"<b>Nutrition Facts:</b> {pi.get('nutritional_panel', {}).get('status', 'Not Detected')}"
    )
    story.append(Paragraph(pi_summary_text, cell_style))
    story.append(Spacer(1, 4))

    if additives:
        additive_rows = [
            [
                Paragraph("<b>INS Code</b>", cell_bold),
                Paragraph("<b>Common Chemical Name</b>", cell_bold),
                Paragraph("<b>Functional Class</b>", cell_bold),
                Paragraph("<b>Safety / Risk Level</b>", cell_bold),
                Paragraph("<b>Regulatory Status</b>", cell_bold),
            ]
        ]
        for a in additives:
            risk = a.get("risk_level", "green")
            r_color = "#16a34a" if risk == "green" else ("#d97706" if risk == "yellow" else "#dc2626")
            r_badge = f"<font color='{r_color}'><b>{risk.upper()}</b></font>"

            additive_rows.append([
                Paragraph(a.get("identifier", ""), cell_bold),
                Paragraph(a.get("common_name", ""), cell_style),
                Paragraph(a.get("function", ""), cell_style),
                Paragraph(r_badge, cell_style),
                Paragraph(a.get("regulatory_status", "")[:80], cell_style),
            ])

        add_table = Table(additive_rows, colWidths=[65, 120, 110, 75, 170])
        add_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(add_table)
        story.append(Spacer(1, 4))

    if allergens:
        allergen_text = "<b>Allergen Alerts:</b> " + "; ".join(
            f"[{a.get('display_name')} — {a.get('detection_type')}]" for a in allergens
        )
        story.append(Paragraph(allergen_text, cell_style))
        story.append(Spacer(1, 4))

    # =========================================================================
    # SECTION 7 — STATUTORY NOTICE, DISCLAIMER & SIGN-OFF
    # =========================================================================
    story.append(Paragraph("SECTION 7 — STATUTORY NOTICE & LEGAL DISCLAIMER", section_heading))

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#475569"),
    )
    story.append(Paragraph(
        "<b>Statutory Notice:</b> This automated compliance report is rendered pursuant to the Legal Metrology Act, 2009 "
        "and Legal Metrology (Packaged Commodities) Rules, 2011. Non-declarations and misleading statements are cognizable offenses "
        "under Section 36 of the Legal Metrology Act, 2009.<br/>"
        "<b>Product Intelligence Disclaimer:</b> Product intelligence and additive decoding are provided for informational "
        "assistance and derived objectively from recognized statutory label typography and authoritative food safety databases (FSSAI/Codex). "
        "Final administrative enforcement determinations remain solely with authorized Legal Metrology officers.",
        disclaimer_style,
    ))
    story.append(Spacer(1, 10))

    # Digital Seal & Signatures
    sign_data = [
        [
            Paragraph(f"<b>Inspecting Authority:</b><br/>{inspector_name}<br/>Legal Metrology Inspector", cell_style),
            Paragraph("<b>Verification Portal Seal:</b><br/>[OFFICIALLY AUDITED & CERTIFIED]<br/>Govt. Legal Metrology Portal", cell_style),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(
        TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(sign_table)

    doc.build(story)
    return buffer.getvalue()
