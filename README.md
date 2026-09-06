# Legal Metrology Compliance Checking System
### Automated Label Verification under India's Legal Metrology (Packaged Commodities) Rules, 2011

A full-stack, automated computer vision and compliance auditing platform built for enforcement inspectors and packaging manufacturers. It ingests product packaging photos, performs OpenCV preprocessing and contour-based label region detection, runs EasyOCR (with pytesseract fallback), extracts mandatory statutory declarations via regex pattern recognition, validates them against the Legal Metrology Rules 2011, and generates real-time compliance scores, interactive reports, downloadable PDF inspection orders, and an executive analytics dashboard.

---

## Key Features

1. **Computer Vision Preprocessing & Contour Cropping (OpenCV)**:
   - Automated grayscale conversion, Non-Local Means Denoising (`fastNlMeansDenoising`), minAreaRect text deskewing, and CLAHE contrast enhancement.
   - Largest rectangular contour detection to isolate and crop the label packaging area.
2. **Hybrid OCR Engine**:
   - Primary EasyOCR pipeline with lazy singleton model initialization.
   - Automatic confidence scoring and fallback to pytesseract for low-contrast or ambiguous text.
3. **Regulatory Rule Engine (Rules, 2011)**:
   - **LM-01**: Manufacturer / Packer / Importer Name & Address (Rule 6(1)(a)) [Major]
   - **LM-02**: Net Quantity Declaration in standard metric units (Rule 6(1)(b) & Rule 12) [Major]
   - **LM-03**: Maximum Retail Price (MRP) with mandatory "inclusive of all taxes" (Rule 6(1)(e)) [Major]
   - **LM-04**: Month & Year of Manufacture / Packing / Import (Rule 6(1)(d)) [Major]
   - **LM-05**: Consumer Care Details (Phone / Toll-free / Email) (Rule 6(1)(n)) [Minor]
   - **LM-06**: FSSAI License Number (14-digit) for food commodities [Major]
   - **LM-07**: Country of Origin declaration [Minor]
4. **Interactive Executive Dashboard (React + Recharts + Tailwind CSS)**:
   - Real-time statutory metrics: Total Audits, Compliant vs Non-Compliant Counts, Overall Compliance Rate (%).
   - Dynamic timeline line charts and rule violation distribution bar charts.
   - Searchable and filterable past inspection audit trail.
5. **Instant 1-Click Hackathon Demo**:
   - Pre-bundled sample test labels (Fully Compliant Biscuit, Non-Compliant Chocolate Bar with missing taxes clause, and Partial Herbal Soap) for immediate live testing without needing physical packaging.
   - Pre-seeded realistic demo database records for instant dashboard visual presentation.
6. **Statutory PDF Report Generation (ReportLab)**:
   - One-click export of official Directorate of Legal Metrology compliance reports with metadata, visual pass/fail badges, violations table, extracted fields, and digital sign-off blocks.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS, Recharts, Lucide Icons, Axios, Vite |
| **Backend** | FastAPI, Python 3.13, Pydantic v2 |
| **Authentication** | JWT (JSON Web Tokens) with direct bcrypt hashing & role-based access |
| **Computer Vision** | OpenCV (`opencv-python`), NumPy, Pillow |
| **OCR** | EasyOCR (primary), PyTorch, pytesseract (fallback) |
| **Rule Engine** | Custom Python statutory engine (Rules, 2011 checklist) |
| **Database** | SQLite (development) / PostgreSQL (production via SQLAlchemy) |
| **Report Generation**| ReportLab PDF Engine |

---

## Project Structure

```
legal-metrology-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, static mounts, lifespan DB seeder
│   │   ├── db.py                   # SQLAlchemy engine, sessionmaker, DB seed
│   │   ├── auth/                   # JWT auth, bcrypt hashing, dependencies
│   │   ├── models/                 # SQLAlchemy models (User, Inspection, Violation, Rule)
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   ├── routers/                # /auth, /inspections, /dashboard
│   │   ├── cv_pipeline/            # OpenCV denoise, deskew, contour crop
│   │   ├── ocr/                    # EasyOCR & pytesseract fallback wrapper
│   │   ├── extraction/             # Regex-based field extraction
│   │   ├── rule_engine/            # Legal Metrology Rules, 2011 validation logic
│   │   └── reports/                # ReportLab PDF report generator
│   ├── sample_images/              # Compliant and non-compliant label samples
│   ├── storage/                    # Uploaded & cropped images storage
│   ├── requirements.txt            # Python dependencies
│   ├── seed_demo_data.py           # Pre-seeds realistic audits for dashboard
│   └── tests/
│       ├── test_pipeline.py        # CV, OCR, regex, rule engine & PDF tests
│       └── test_api.py             # FastAPI TestClient endpoint tests
├── frontend/
│   ├── src/
│   │   ├── api/                    # Axios client with JWT interceptor
│   │   ├── components/             # Navbar, StatCard, StatusBadge, ScoreGauge
│   │   ├── pages/                  # Login, Upload, Report, Dashboard, History
│   │   ├── App.jsx                 # Routing & state management
│   │   └── index.css               # Tailwind CSS directives
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
└── README.md
```

---

## Quick Start Guide

### 1. Backend Setup

From the `backend` directory:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Pre-generate sample label images (optional, already bundled)
python generate_samples.py

# 3. Seed demo inspections (populates dashboard stats)
python seed_demo_data.py

# 4. Run automated test suite
python -m pytest tests/ -v

# 5. Start the backend API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API interactive documentation will be live at: `http://localhost:8000/docs`

### 2. Frontend Setup

From the `frontend` directory:

```bash
# 1. Install dependencies
npm install

# 2. Start the Vite development server
npm run dev
```

The frontend will be available at: `http://localhost:5173`

---

## Demo Accounts

You can click any of the 1-click quick-login buttons on the login screen or enter:

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Inspector** | `inspector@gov.in` | `inspector123` | Full upload, inspection & report generation |
| **Admin** | `admin@gov.in` | `admin123` | System oversight & compliance analytics |
| **Viewer** | `viewer@gov.in` | `viewer123` | Read-only inspection viewing & reports |

---

## How to Test the Demo Flow (30 seconds)

1. Open `http://localhost:5173` and click **"Inspector"** quick-login.
2. The **Dashboard** loads with real statistics, compliance trend lines, and violation breakdowns.
3. Click **"New Inspection"** in the top navigation.
4. In the **"Quick Sample Test"** section, click **"Compliant Biscuit Label"** (or upload any real packaged commodity photo).
5. Click **"Execute Compliance Verification"**.
6. Watch the live progress meter run through OpenCV deskewing, contour cropping, EasyOCR extraction, and rule evaluation.
7. The **Report View** appears displaying:
   - Compliance score (100% Fully Compliant).
   - Side-by-side original image vs OpenCV cropped label contour.
   - Statutory checklist with green pass badges.
   - Structured extracted fields (MRP, Net Qty, Mfg Date, FSSAI, Customer Care).
8. Click **"Download PDF Report"** to download the official ReportLab inspection order.
9. Try testing the **"Non-Compliant Chocolate Bar"** sample to see red failure badges on missing taxes declaration and missing consumer care.

---

## Deployment to Render / Railway

### Backend (`render.yaml` or Railway Procfile)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `DATABASE_URL`: PostgreSQL connection string (defaults to SQLite if omitted)
  - `JWT_SECRET_KEY`: Production secret key

### Frontend
- **Build Command**: `npm run build`
- **Publish Directory**: `dist`
- **Environment Variables**:
  - `VITE_API_URL`: Your deployed backend URL (e.g. `https://legal-metrology-api.onrender.com`)


### running web app
## Start backend
    cd backend
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
## Start frontend
    cd frontend
    npm.cmd run dev

