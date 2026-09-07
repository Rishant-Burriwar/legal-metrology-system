import io
from datetime import datetime
from typing import Dict, Any, List
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
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )
    cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
    )

    story = []

    # Title & Header
    story.append(Paragraph("DIRECTORATE OF LEGAL METROLOGY", subtitle_style))
    story.append(Paragraph("PACKAGED COMMODITIES COMPLIANCE REPORT", title_style))
    story.append(Paragraph("Verification under Legal Metrology (Packaged Commodities) Rules, 2011", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

    # Inspection Metadata Table
    status_bg = colors.HexColor("#dcfce7") if overall_status == "Compliant" else colors.HexColor("#fee2e2")
    status_text_color = "#166534" if overall_status == "Compliant" else "#991b1b"

    status_html = f"<font color='{status_text_color}'><b>{overall_status.upper()} ({compliance_score}%)</b></font>"

    meta_data = [
        [
            Paragraph("<b>Inspection ID:</b>", cell_style),
            Paragraph(f"#{inspection_id:05d}", cell_bold),
            Paragraph("<b>Inspection Date:</b>", cell_style),
            Paragraph(created_at.strftime("%d-%b-%Y %H:%M UTC") if isinstance(created_at, datetime) else str(created_at), cell_style),
        ],
        [
            Paragraph("<b>Product Name:</b>", cell_style),
            Paragraph(product_name, cell_bold),
            Paragraph("<b>Brand:</b>", cell_style),
            Paragraph(brand, cell_style),
        ],
        [
            Paragraph("<b>Inspector:</b>", cell_style),
            Paragraph(inspector_name, cell_style),
            Paragraph("<b>Inspection Zone:</b>", cell_style),
            Paragraph(location, cell_style),
        ],
        [
            Paragraph("<b>Overall Compliance:</b>", cell_style),
            Paragraph(status_html, cell_bold),
            Paragraph("<b>Rules Evaluated:</b>", cell_style),
            Paragraph(f"{len(violations)} Mandatory Declarations", cell_style),
        ],
        [
            Paragraph("<b>Image Quality Score:</b>", cell_style),
            Paragraph(f"{quality_score:.1f} / 100", cell_style),
            Paragraph("<b>Inspection AI Engine:</b>", cell_style),
            Paragraph(str(extracted_data.get("_ai_engine", "Gemini Multimodal Vision AI")), cell_bold),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[110, 160, 110, 160])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Violations / Checklist Section
    story.append(Paragraph("Mandatory Declarations Evaluation (Rule 6, Rules 2011)", section_heading))

    checklist_data = [
        [
            Paragraph("<b>Rule Code</b>", cell_bold),
            Paragraph("<b>Declaration / Rule Description</b>", cell_bold),
            Paragraph("<b>Severity</b>", cell_bold),
            Paragraph("<b>Result</b>", cell_bold),
        ]
    ]

    for v in violations:
        rule_code = v.get("rule_code", "")
        desc = v.get("description", "")
        sev = v.get("severity", "Major")
        st = v.get("status", "Pass")

        st_color = "#16a34a" if st == "Pass" else "#dc2626"
        sev_color = "#b91c1c" if sev == "Major" else "#d97706"

        checklist_data.append([
            Paragraph(f"<b>{rule_code}</b>", cell_style),
            Paragraph(desc, cell_style),
            Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", cell_style),
            Paragraph(f"<font color='{st_color}'><b>{st.upper()}</b></font>", cell_bold),
        ])

    checklist_table = Table(checklist_data, colWidths=[65, 345, 65, 65])
    checklist_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(checklist_table)
    story.append(Spacer(1, 14))

    # Extracted Fields Section
    story.append(Paragraph("Extracted Label Declarations (OCR & NLP Data)", section_heading))

    extracted_rows = [
        [
            Paragraph("<b>Declaration Field</b>", cell_bold),
            Paragraph("<b>Extracted Value from Label</b>", cell_bold),
            Paragraph("<b>Detection Status</b>", cell_bold),
        ]
    ]

    field_labels = {
        "manufacturer_details": "Manufacturer / Packer Details",
        "net_quantity": "Net Quantity",
        "mrp": "Maximum Retail Price (MRP)",
        "manufacture_date": "Date of Mfg / Pkg",
        "customer_care": "Consumer Care Info",
        "fssai_license": "FSSAI License Number",
        "country_of_origin": "Country of Origin",
    }

    if extracted_data:
        for k, lbl in field_labels.items():
            finfo = extracted_data.get(k, {})
            val = finfo.get("value") or "Not Detected"
            det_status = finfo.get("status", "not_found").replace("_", " ").title()

            st_color = "#16a34a" if finfo.get("status") == "found" else (
                "#d97706" if finfo.get("status") == "low_confidence" else "#dc2626"
            )

            extracted_rows.append([
                Paragraph(f"<b>{lbl}</b>", cell_style),
                Paragraph(str(val), cell_style),
                Paragraph(f"<font color='{st_color}'>{det_status}</font>", cell_style),
            ])

    ext_table = Table(extracted_rows, colWidths=[150, 300, 90])
    ext_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(ext_table)
    story.append(Spacer(1, 20))

    # Sign-off & Disclaimer
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )
    story.append(Paragraph(
        "<b>Statutory Notice:</b> This automated compliance report is generated under the provisions of the Legal Metrology Act, 2009 "
        "and Legal Metrology (Packaged Commodities) Rules, 2011. Violations are punishable under Section 36 of the Legal Metrology Act, 2009.",
        disclaimer_style,
    ))
    story.append(Spacer(1, 20))

    # Signatures
    sign_data = [
        [
            Paragraph(f"<b>Inspecting Authority:</b><br/>{inspector_name}<br/>Legal Metrology Inspector", cell_style),
            Paragraph("<b>Official Seal:</b><br/>[DIGITALLY VERIFIED]<br/>Govt. Legal Metrology Portal", cell_style),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(
        TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(sign_table)

    doc.build(story)
    return buffer.getvalue()
