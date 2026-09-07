import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal, Base, engine, seed_database
from app.models.models import Inspection, Violation, User
from app.extraction.extractor import extract_compliance_fields
from app.rule_engine.rules import evaluate_compliance


def seed_demo_inspections():
    Base.metadata.create_all(bind=engine)
    seed_database()

    db = SessionLocal()
    try:
        insp1 = db.query(User).filter(User.email == "inspector@gov.in").first()
        insp2 = db.query(User).filter(User.email == "inspector2@gov.in").first()
        admin_u = db.query(User).filter(User.email == "admin@gov.in").first()
        user_ids = [
            insp1.id if insp1 else 1,
            insp2.id if insp2 else (insp1.id if insp1 else 1),
            admin_u.id if admin_u else 1,
        ]

        existing_count = db.query(Inspection).count()
        if existing_count >= 5:
            print(f"Database already contains {existing_count} inspections.")
            return

        demo_products = [
            {
                "product": "NutriCrunch Almond Cookies 250g",
                "brand": "Suncrest Foods",
                "ocr": """NUTRICRUNCH ALMOND COOKIES
Manufactured by: Suncrest Foods Pvt. Ltd., Plot 42, Okhla Ind Area, New Delhi - 110020
Net Quantity: 250 g
MRP: Rs. 85.00 (incl. of all taxes)
Mfg Date: 08/2026
Customer Care: 1800-112-4999, care@suncrestfoods.in
FSSAI Lic No: 10015011000234
Country of Origin: India""",
                "image": "/sample_images/compliant_label.png",
                "days_ago": 4,
            },
            {
                "product": "ChocoDelight Premium Bar 50g",
                "brand": "ChocoDelight",
                "ocr": """CHOCODELIGHT BAR
Manufactured by: ChocoDelight Works
Net Quantity: 50 g
MRP: Rs. 40.00
Mfg Date: 12/2025""",
                "image": "/sample_images/non_compliant_label.png",
                "days_ago": 3,
            },
            {
                "product": "Himalayan Herbal Handmade Soap",
                "brand": "AyurVeda Organics",
                "ocr": """HIMALAYAN HERBAL HANDMADE SOAP
Manufactured by: AyurVeda Organics Ltd, Dehradun, Uttarakhand - 248001
Net Quantity: 125 g
MRP: Rs. 65.00 (incl. of all taxes)
PKD: 05/2026
Customer Care: 9876543210
Country of Origin: India""",
                "image": "/sample_images/partial_label.png",
                "days_ago": 2,
            },
            {
                "product": "Golden Harvest Basmati Rice 5kg",
                "brand": "Golden Harvest",
                "ocr": """GOLDEN HARVEST PREMIUM BASMATI RICE
Packed by: Golden Harvest Agro Ltd, Karnal, Haryana - 132001
Net Quantity: 5 kg
MRP: Rs. 480.00 (incl. of all taxes)
Packed: 07/2026
Customer Care: 1800-200-8888, care@goldenharvest.in
FSSAI Lic No: 10018022000789
Country of Origin: India""",
                "image": "/sample_images/compliant_label.png",
                "days_ago": 1,
            },
            {
                "product": "Sparkle Dishwash Gel 500ml",
                "brand": "Sparkle Hygiene",
                "ocr": """SPARKLE ULTRA DISHWASH GEL
Marketed by: Sparkle Hygiene Products
MRP: 99.00
PKD: 06/2026""",
                "image": "/sample_images/non_compliant_label.png",
                "days_ago": 0,
            },
        ]

        for idx, item in enumerate(demo_products):
            created_at = datetime.now(timezone.utc) - timedelta(days=item["days_ago"], hours=item["days_ago"] * 2)
            fields = extract_compliance_fields(item["ocr"])
            score, status, validations = evaluate_compliance(fields, is_food_product=True)
            assigned_user_id = user_ids[idx % len(user_ids)]

            insp = Inspection(
                inspector_id=assigned_user_id,
                product_name=item["product"],
                brand=item["brand"],
                image_path=item["image"],
                cropped_image_path=item["image"],
                raw_ocr_text=item["ocr"],
                extracted_data=fields,
                compliance_score=score,
                overall_status=status,
                created_at=created_at,
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)

            for v in validations:
                violation = Violation(
                    inspection_id=insp.id,
                    rule_code=v["rule_code"],
                    description=v["description"],
                    severity=v["severity"],
                    status=v["status"],
                )
                db.add(violation)
            db.commit()

        print("Successfully seeded demo inspections!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_inspections()
