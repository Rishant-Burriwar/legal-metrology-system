import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, seed_database, SessionLocal
from app.models.models import User, Inspection

Base.metadata.create_all(bind=engine)
seed_database()

client = TestClient(app)
SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_images"))


def get_token_for(email: str, password: str = "inspector123") -> str:
    pwd = "admin123" if email == "admin@gov.in" else ("viewer123" if email == "viewer@gov.in" else "inspector123")
    res = client.post("/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 200, f"Failed login for {email}: {res.text}"
    return res.json()["access_token"]


def test_inspector_dashboard_and_list_isolation():
    """Inspector Sharma should only see his own inspections and stats."""
    token_sharma = get_token_for("inspector@gov.in")
    headers_sharma = {"Authorization": f"Bearer {token_sharma}"}

    # Dashboard stats
    res = client.get("/dashboard/stats", headers=headers_sharma)
    assert res.status_code == 200
    data = res.json()
    assert data["user_role"] == "inspector"
    assert data["inspector_name"] == "Senior Inspector Sharma"
    assert data["inspectors_progress"] is None  # Not shown to inspector

    sharma_total = data["total_inspections"]

    # List inspections
    list_res = client.get("/inspections", headers=headers_sharma)
    assert list_res.status_code == 200
    inspections = list_res.json()
    for insp in inspections:
        assert insp["inspector_name"] == "Senior Inspector Sharma"


def test_inspector2_dashboard_isolation():
    """Inspector Priya Patel should only see her own inspections."""
    token_priya = get_token_for("inspector2@gov.in")
    headers_priya = {"Authorization": f"Bearer {token_priya}"}

    res = client.get("/dashboard/stats", headers=headers_priya)
    assert res.status_code == 200
    data = res.json()
    assert data["user_role"] == "inspector"
    assert data["inspector_name"] == "Inspector Priya Patel"
    assert data["inspectors_progress"] is None

    list_res = client.get("/inspections", headers=headers_priya)
    assert list_res.status_code == 200
    for insp in list_res.json():
        assert insp["inspector_name"] == "Inspector Priya Patel"


def test_admin_dashboard_and_inspectors_progress():
    """Admin should see department-wide stats and the progress of all other inspectors."""
    token_admin = get_token_for("admin@gov.in")
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    res = client.get("/dashboard/stats", headers=headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["user_role"] == "admin"
    assert data["inspectors_progress"] is not None
    assert len(data["inspectors_progress"]) >= 2

    # Check that both inspectors exist in progress breakdown
    names = [p["name"] for p in data["inspectors_progress"]]
    assert "Senior Inspector Sharma" in names
    assert "Inspector Priya Patel" in names

    # Inspect the fields of the progress summary
    for p in data["inspectors_progress"]:
        assert "total_inspections" in p
        assert "compliance_rate" in p
        assert "avg_score" in p


def test_admin_inspect_product_updates_dashboard():
    """Admin can inspect products, and it updates their dashboard with inspector_id = admin.id."""
    token_admin = get_token_for("admin@gov.in")
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Initial admin stats
    init_stats = client.get("/dashboard/stats", headers=headers_admin).json()
    init_total = init_stats["total_inspections"]

    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/inspections/upload",
        files={"images": ("compliant_label.png", file_bytes, "image/png")},
        data={
            "product_name": "Admin Test Sample Cookies",
            "brand": "AdminBrand",
            "is_food_product": "true",
            "ai_engine": "local",
        },
        headers=headers_admin,
    )
    assert upload_res.status_code == 200
    insp_data = upload_res.json()
    assert insp_data["product_name"] == "Admin Test Sample Cookies"

    # Verify dashboard total incremented
    new_stats = client.get("/dashboard/stats", headers=headers_admin).json()
    assert new_stats["total_inspections"] == init_total + 1


def test_viewer_cannot_inspect_products():
    """Viewer should receive 403 Forbidden when attempting to upload and inspect."""
    token_viewer = get_token_for("viewer@gov.in")
    headers_viewer = {"Authorization": f"Bearer {token_viewer}"}

    sample_path = os.path.join(SAMPLE_DIR, "compliant_label.png")
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/inspections/upload",
        files={"images": ("compliant_label.png", file_bytes, "image/png")},
        data={
            "product_name": "Viewer Attempt",
            "brand": "ForbiddenBrand",
            "is_food_product": "true",
        },
        headers=headers_viewer,
    )
    assert res.status_code == 403
    assert "Viewers have read-only access" in res.json()["detail"]


def test_viewer_can_list_and_download_reports():
    """Viewer can list inspections and download PDF reports without hindrance."""
    token_viewer = get_token_for("viewer@gov.in")
    headers_viewer = {"Authorization": f"Bearer {token_viewer}"}

    # List past inspections
    list_res = client.get("/inspections", headers=headers_viewer)
    assert list_res.status_code == 200
    inspections = list_res.json()
    assert len(inspections) > 0

    first_id = inspections[0]["id"]

    # Download PDF report
    pdf_res = client.get(f"/inspections/{first_id}/report.pdf", headers=headers_viewer)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000  # valid PDF binary stream
