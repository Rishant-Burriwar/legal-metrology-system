from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models.models import Inspection, Violation, Rule, User
from app.schemas.schemas import DashboardStats, ViolationBreakdown, InspectorProgressSummary
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    inspector_id: Optional[int] = Query(None, description="Optional filter by inspector ID for admin"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get role-aware compliance statistics for dashboard:
    - Inspector: Only sees their own inspection statistics and trend.
    - Admin: Department-wide statistics, optional filter by inspector_id, plus detailed inspectors_progress tracker.
    - Viewer: Overall compliance overview in read-only format.
    """
    target_inspector_id: Optional[int] = None
    target_inspector_name: Optional[str] = None

    if current_user.role == "inspector":
        target_inspector_id = current_user.id
        target_inspector_name = current_user.name
    elif current_user.role == "admin":
        if inspector_id is not None:
            target_inspector_id = inspector_id
            insp_user = db.query(User).filter(User.id == inspector_id).first()
            target_inspector_name = insp_user.name if insp_user else f"Inspector #{inspector_id}"
    # Viewer sees department-wide overview (target_inspector_id is None)

    # Base inspection query
    insp_query = db.query(Inspection)
    if target_inspector_id is not None:
        insp_query = insp_query.filter(Inspection.inspector_id == target_inspector_id)

    total = insp_query.count()
    compliant = insp_query.filter(Inspection.overall_status == "Compliant").count()
    non_compliant = insp_query.filter(Inspection.overall_status == "Non-Compliant").count()

    compliance_rate = round((compliant / total * 100.0), 1) if total > 0 else 0.0

    # Rule definitions
    rules = db.query(Rule).all()
    rule_map = {r.rule_code: r.description for r in rules}

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
    viol_query = db.query(
        Violation.rule_code,
        Violation.status,
        func.count(Violation.id).label("count"),
    )
    if target_inspector_id is not None:
        viol_query = viol_query.join(Inspection, Violation.inspection_id == Inspection.id).filter(
            Inspection.inspector_id == target_inspector_id
        )
    violation_counts = viol_query.group_by(Violation.rule_code, Violation.status).all()

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
    trend_query = db.query(Inspection)
    if target_inspector_id is not None:
        trend_query = trend_query.filter(Inspection.inspector_id == target_inspector_id)

    recent_inspections = (
        trend_query
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

    # For Admin: compute inspector progress across all inspectors and admins
    inspectors_progress: Optional[List[InspectorProgressSummary]] = None
    if current_user.role == "admin":
        team_users = db.query(User).filter(User.role.in_(["inspector", "admin"])).all()
        inspectors_progress = []
        for u in team_users:
            u_insps = db.query(Inspection).filter(Inspection.inspector_id == u.id).all()
            u_total = len(u_insps)
            u_compliant = sum(1 for i in u_insps if i.overall_status == "Compliant")
            u_non_compliant = sum(1 for i in u_insps if i.overall_status == "Non-Compliant")
            u_rate = round((u_compliant / u_total * 100.0), 1) if u_total > 0 else 0.0
            u_avg_score = (
                round(sum(i.compliance_score for i in u_insps) / u_total, 1)
                if u_total > 0
                else 0.0
            )
            last_dt = max((i.created_at for i in u_insps), default=None)

            inspectors_progress.append(
                InspectorProgressSummary(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    role=u.role,
                    total_inspections=u_total,
                    compliant_count=u_compliant,
                    non_compliant_count=u_non_compliant,
                    compliance_rate=u_rate,
                    avg_score=u_avg_score,
                    last_inspection_at=last_dt,
                )
            )

    return DashboardStats(
        total_inspections=total,
        compliant_count=compliant,
        non_compliant_count=non_compliant,
        compliance_rate=compliance_rate,
        violations_by_type=breakdown_list,
        recent_trend=trend,
        user_role=current_user.role,
        inspector_name=target_inspector_name or current_user.name,
        inspector_filter_id=target_inspector_id,
        inspectors_progress=inspectors_progress,
    )
