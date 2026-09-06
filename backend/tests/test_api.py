import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, seed_database

# Initialize DB for tests
Base.metadata.create_all(bind=engine)
seed_database()

client = TestClient(app)


def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_login_inspector():
    response = client.post(
        "/auth/login",
        json={"email": "inspector@gov.in", "password": "inspector123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "inspector"
    assert data["token_type"] == "bearer"


def test_auth_login_invalid():
    response = client.post(
        "/auth/login",
        json={"email": "inspector@gov.in", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_dashboard_stats_and_upload():
    # Login first
    login_res = client.post(
        "/auth/login",
        json={"email": "inspector@gov.in", "password": "inspector123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check stats endpoint
    stats_res = client.get("/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_inspections" in stats
    assert "violations_by_type" in stats

    # Test Upload with compliant sample image
    sample_path = os.path.join(
        os.path.dirname(__file__), "..", "sample_images", "compliant_label.png"
    )
    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/inspections/upload",
        files={"image": ("compliant_label.png", file_bytes, "image/png")},
        data={"product_name": "NutriCrunch Cookies", "brand": "Suncrest", "is_food_product": "true"},
        headers=headers,
    )
    assert upload_res.status_code == 200
    insp = upload_res.json()
    assert insp["id"] is not None
    assert "compliance_score" in insp
    assert len(insp["violations"]) > 0

    insp_id = insp["id"]

    # Test GET inspection details
    get_res = client.get(f"/inspections/{insp_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == insp_id

    # Test PDF download
    pdf_res = client.get(f"/inspections/{insp_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
