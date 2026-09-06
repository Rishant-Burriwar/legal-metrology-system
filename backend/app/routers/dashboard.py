from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models.models import Inspection, Violation, Rule, User
from app.schemas.schemas import DashboardStats, ViolationBreakdown
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregate compliance statistics for executive dashboard:
    - Total, Compliant, Non-compliant counts
    - Overall Compliance Rate (%)
    - Breakdown of violations by Legal Metrology rule code
    - Timeline trend for compliance charts
    """
    total = db.query(Inspection).count()
    compliant = db.query(Inspection).filter(Inspection.overall_status == "Compliant").count()
    non_compliant = db.query(Inspection).filter(Inspection.overall_status == "Non-Compliant").count()

    compliance_rate = round((compliant / total * 100.0), 1) if total > 0 else 0.0

    # Rule definitions
    rules = db.query(Rule).all()
    rule_map = {r.rule_code: r.description for r in rules}

    # Fallback descriptions if DB not yet queried
    if not rule_map:
        rule_map = {
            "LM-01": "Manufacturer Details (Rule 6(1)(a))",
            "LM-02": "Net Quantity (Rule 6(1)(b))",
            "LM-03": "MRP incl. Taxes (Rule 6(1)(e))",
            "LM-04": "Date of Mfg / Pkg (Rule 6(1)(d))",
            "LM-05": "Customer Care Contact (Rule 6(1)(n))",
            "LM-06": "FSSAI Food License",
            "LM-07": "Country of Origin",
        }

    # Aggregate violations by rule code
    violation_counts = (
        db.query(
            Violation.rule_code,
            Violation.status,
            func.count(Violation.id).label("count"),
        )
        .group_by(Violation.rule_code, Violation.status)
        .all()
    )

    stats_by_code: Dict[str, Dict[str, int]] = {
        code: {"fail": 0, "pass": 0} for code in rule_map.keys()
    }

    for rule_code, st, cnt in violation_counts:
        if rule_code not in stats_by_code:
            stats_by_code[rule_code] = {"fail": 0, "pass": 0}
        if st == "Fail":
            stats_by_code[rule_code]["fail"] += cnt
        else:
            stats_by_code[rule_code]["pass"] += cnt

    breakdown_list = [
        ViolationBreakdown(
            rule_code=code,
            description=rule_map.get(code, code),
            fail_count=counts["fail"],
            pass_count=counts["pass"],
        )
        for code, counts in stats_by_code.items()
    ]

    # Recent inspections for trend chart
    recent_inspections = (
        db.query(Inspection)
        .order_by(Inspection.created_at.asc())
        .limit(30)
        .all()
    )

    trend = []
    for insp in recent_inspections:
        trend.append({
            "id": insp.id,
            "label": f"#{insp.id:03d}",
            "date": insp.created_at.strftime("%d %b"),
            "product": insp.product_name,
            "score": insp.compliance_score,
            "status": insp.overall_status,
        })

    return DashboardStats(
        total_inspections=total,
        compliant_count=compliant,
        non_compliant_count=non_compliant,
        compliance_rate=compliance_rate,
        violations_by_type=breakdown_list,
        recent_trend=trend,
    )
