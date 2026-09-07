import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./legal_metrology.db")

# Render/Railway postgres url fix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Ensure newly added columns exist in existing database tables."""
    from sqlalchemy import text
    try:
        if DATABASE_URL.startswith("sqlite"):
            with engine.begin() as conn:
                cursor = conn.execute(text("PRAGMA table_info(inspections)"))
                existing_cols = {row[1] for row in cursor.fetchall()}
                if existing_cols:
                    columns_to_add = [
                        ("validated_ocr_text", "TEXT"),
                        ("ocr_confidence", "FLOAT DEFAULT 0.0"),
                        ("ocr_retry_count", "INTEGER DEFAULT 0"),
                        ("quality_score", "FLOAT DEFAULT 0.0"),
                        ("quality_assessment", "JSON"),
                    ]
                    for col_name, col_type in columns_to_add:
                        if col_name not in existing_cols:
                            conn.execute(text(f"ALTER TABLE inspections ADD COLUMN {col_name} {col_type}"))
    except Exception:
        pass


# Run migrations immediately on initialization
run_migrations()


def seed_database():
    from app.models.models import Rule, User
    from app.auth.jwt import get_password_hash

    db = SessionLocal()
    try:
        # Seed default users
        existing_users = db.query(User).count()
        if existing_users == 0:
            default_users = [
                User(
                    name="Senior Inspector Sharma",
                    email="inspector@gov.in",
                    hashed_password=get_password_hash("inspector123"),
                    role="inspector",
                ),
                User(
                    name="Admin Controller",
                    email="admin@gov.in",
                    hashed_password=get_password_hash("admin123"),
                    role="admin",
                ),
                User(
                    name="Public Viewer",
                    email="viewer@gov.in",
                    hashed_password=get_password_hash("viewer123"),
                    role="viewer",
                ),
            ]
            db.add_all(default_users)
            db.commit()

        # Seed mandatory Legal Metrology (Packaged Commodities) Rules, 2011
        existing_rules = db.query(Rule).count()
        if existing_rules == 0:
            rules_seed = [
                Rule(
                    rule_code="LM-01",
                    description="Name and complete address of the manufacturer / packer / importer (Rule 6(1)(a))",
                    severity="Major",
                ),
                Rule(
                    rule_code="LM-02",
                    description="Net quantity in standard unit of weight, measure or number (Rule 6(1)(b) & Rule 12)",
                    severity="Major",
                ),
                Rule(
                    rule_code="LM-03",
                    description="Maximum Retail Price (MRP) inclusive of all taxes (Rule 6(1)(e))",
                    severity="Major",
                ),
                Rule(
                    rule_code="LM-04",
                    description="Month and year of manufacture / packing / import (Rule 6(1)(d))",
                    severity="Major",
                ),
                Rule(
                    rule_code="LM-05",
                    description="Consumer care details with name, address, phone/toll-free number, and email (Rule 6(1)(n))",
                    severity="Minor",
                ),
                Rule(
                    rule_code="LM-06",
                    description="FSSAI License number (14-digit) for food and edible commodities",
                    severity="Major",
                ),
                Rule(
                    rule_code="LM-07",
                    description="Country of origin clearly stated on the package",
                    severity="Minor",
                ),
            ]
            db.add_all(rules_seed)
            db.commit()
    finally:
        db.close()
