import re
from typing import Dict, Any, Optional


def clean_text_field(text: str) -> str:
    """Strip unnecessary whitespace and clean characters."""
    return re.sub(r"\s+", " ", text).strip()


def extract_manufacturer_details(ocr_text: str) -> Dict[str, Any]:
    # Look for Manufactured by / Packed by / Marketed by
    pattern = re.compile(
        r"(?:Mfg\b|Manufactured\s+by|Marketed\s+by|Packed\s+by|Imported\s+by|Pkd\s+by)[\s\:\-]+(.+?)(?=(?:MRP|Net\s*Q|Best\s*Before|Customer|FSSAI|Country|$))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(ocr_text)

    if match:
        raw_val = clean_text_field(match.group(1))
        # Check if address contains useful details (e.g. city/state/pin/pvt/ltd)
        if len(raw_val) >= 10:
            return {
                "value": raw_val[:180],
                "status": "found",
                "raw_snippet": match.group(0)[:200],
            }
        return {
            "value": raw_val,
            "status": "low_confidence",
            "raw_snippet": match.group(0)[:100],
        }

    # Secondary heuristic: Look for company names with Ltd / Pvt / Works
    co_pattern = re.compile(
        r"([A-Z][A-Za-z0-9\s.,&-]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Industries|Foods|Enterprises|Corporation)[^\n\r]*)",
        re.IGNORECASE,
    )
    co_match = co_pattern.search(ocr_text)
    if co_match:
        val = clean_text_field(co_match.group(1))
        return {
            "value": val[:180],
            "status": "low_confidence",
            "raw_snippet": co_match.group(0)[:150],
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_net_quantity(ocr_text: str) -> Dict[str, Any]:
    # Match Net Qty / Net Wt followed by number and standard metric unit
    pattern = re.compile(
        r"(?:Net\s*(?:Quantity|Qty|Weight|Wt|Volume|Vol)?[.:\s]*)?(\b\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|grams|ml|l|ltr|litres|liters|pieces|pcs|units|N|count)\b)",
        re.IGNORECASE,
    )
    # Prefer matches that explicitly have Net Qty / Wt
    explicit_pattern = re.compile(
        r"Net\s*(?:Quantity|Qty|Weight|Wt|Volume|Vol)[.:\s]*(\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|grams|ml|l|ltr|litres|liters|pieces|pcs|units|N)\b)",
        re.IGNORECASE,
    )
    exp_match = explicit_pattern.search(ocr_text)
    if exp_match:
        return {
            "value": clean_text_field(exp_match.group(1)),
            "status": "found",
            "raw_snippet": exp_match.group(0),
        }

    match = pattern.search(ocr_text)
    if match:
        return {
            "value": clean_text_field(match.group(1)),
            "status": "found",
            "raw_snippet": match.group(0),
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_mrp(ocr_text: str) -> Dict[str, Any]:
    # Look for MRP amount
    mrp_pattern = re.compile(
        r"(?:M\.?R\.?P\.?|MRP|Max\s*Retail\s*Price)[.:\s]*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d{1,2})?)",
        re.IGNORECASE,
    )
    taxes_pattern = re.compile(
        r"(?:incl(?:usive)?\.?\s*(?:of)?\s*all\s*taxes|incl\.?\s*taxes)",
        re.IGNORECASE,
    )

    match = mrp_pattern.search(ocr_text)
    has_taxes_decl = bool(taxes_pattern.search(ocr_text))

    if match:
        price = match.group(1)
        full_snippet = match.group(0)
        # Search surrounding window for taxes clause
        start_idx = max(0, match.start() - 20)
        end_idx = min(len(ocr_text), match.end() + 50)
        window = ocr_text[start_idx:end_idx]
        has_taxes_near = bool(taxes_pattern.search(window))

        taxes_ok = has_taxes_decl or has_taxes_near
        formatted_val = f"₹ {price}" + (" (incl. of all taxes)" if taxes_ok else " (taxes NOT declared)")

        return {
            "value": formatted_val,
            "amount": float(price),
            "taxes_included": taxes_ok,
            "status": "found" if taxes_ok else "low_confidence",
            "raw_snippet": window.strip(),
        }

    # Backup: Look for standalone ₹ or Rs.
    price_pattern = re.compile(r"(?:Rs\.?|₹)\s*(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
    p_match = price_pattern.search(ocr_text)
    if p_match:
        price = p_match.group(1)
        return {
            "value": f"₹ {price} (unverified MRP tag)",
            "amount": float(price),
            "taxes_included": False,
            "status": "low_confidence",
            "raw_snippet": p_match.group(0),
        }

    return {"value": None, "amount": None, "taxes_included": False, "status": "not_found", "raw_snippet": None}


def extract_manufacture_date(ocr_text: str) -> Dict[str, Any]:
    # Match patterns like:
    # Mfg Date: 08/2026, 08/26, Aug 2026, PKD: 12/2025, Mfd: 01/2026
    date_pattern = re.compile(
        r"(?:Mfg|Manufactured|Packed|Packing|Pkg|PKD|Mfd|Date|Dt)[.:\s]*(?:Date|Dt)?[:.\s]*"
        r"([0-1]?\d[\/\-\.](?:20\d{2}|\d{2})|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(?:20\d{2}|\d{2}))",
        re.IGNORECASE,
    )
    match = date_pattern.search(ocr_text)
    if match:
        return {
            "value": clean_text_field(match.group(1)),
            "status": "found",
            "raw_snippet": match.group(0),
        }

    # Generic Month/Year e.g., 05/2026
    month_year_pattern = re.compile(r"\b(0[1-9]|1[0-2])[\/\-\.](202\d)\b")
    my_match = month_year_pattern.search(ocr_text)
    if my_match:
        return {
            "value": my_match.group(0),
            "status": "low_confidence",
            "raw_snippet": my_match.group(0),
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_customer_care(ocr_text: str) -> Dict[str, Any]:
    # Phone pattern: Toll-free 1800... or 10-digit mobile or landline
    phone_pattern = re.compile(
        r"(?:(?:Tel|Phone|Ph|Call|Helpline|Toll[\s\-]*Free|Care)[\s.:]*)?(1800[\s\-]?\d{3}[\s\-]?\d{3,4}|[6-9]\d{9}|\b\d{3,5}[\-\s]\d{6,8}\b)",
        re.IGNORECASE,
    )
    email_pattern = re.compile(
        r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        re.IGNORECASE,
    )

    phone_match = phone_pattern.search(ocr_text)
    email_match = email_pattern.search(ocr_text)

    phone_val = clean_text_field(phone_match.group(1)) if phone_match else None
    email_val = clean_text_field(email_match.group(1)) if email_match else None

    if phone_val and email_val:
        return {
            "value": f"Phone: {phone_val}, Email: {email_val}",
            "phone": phone_val,
            "email": email_val,
            "status": "found",
            "raw_snippet": f"{phone_val} | {email_val}",
        }
    elif phone_val or email_val:
        val = f"Phone: {phone_val}" if phone_val else f"Email: {email_val}"
        return {
            "value": val,
            "phone": phone_val,
            "email": email_val,
            "status": "low_confidence",
            "raw_snippet": val,
        }

    return {"value": None, "phone": None, "email": None, "status": "not_found", "raw_snippet": None}


def extract_fssai_license(ocr_text: str) -> Dict[str, Any]:
    # FSSAI is a 14-digit number, often starting with 1
    fssai_explicit = re.compile(
        r"(?:FSSAI|Lic(?:ense)?\.?\s*(?:No)?)[.:\s]*(\d{14})",
        re.IGNORECASE,
    )
    match = fssai_explicit.search(ocr_text)
    if match:
        return {
            "value": match.group(1),
            "status": "found",
            "raw_snippet": match.group(0),
        }

    # 14-digit number standalone heuristic
    num_14 = re.compile(r"\b(1\d{13})\b")
    match_14 = num_14.search(ocr_text)
    if match_14:
        return {
            "value": match_14.group(1),
            "status": "found",
            "raw_snippet": match_14.group(0),
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_country_of_origin(ocr_text: str) -> Dict[str, Any]:
    pattern = re.compile(
        r"(?:Country\s*of\s*Origin|Made\s*in|Product\s*of)[:\s]*([A-Za-z\s]+?)(?=[\n,.]|$)",
        re.IGNORECASE,
    )
    match = pattern.search(ocr_text)
    if match:
        country = clean_text_field(match.group(1))
        if len(country) >= 3:
            return {
                "value": country,
                "status": "found",
                "raw_snippet": match.group(0),
            }

    # Look for "Made in India" or "Origin: India"
    if re.search(r"\b(?:India|Bharat)\b", ocr_text, re.IGNORECASE):
        return {
            "value": "India",
            "status": "found",
            "raw_snippet": "India detected in label text",
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_compliance_fields(ocr_text: str) -> Dict[str, Any]:
    """
    Extract all 7 mandatory Legal Metrology declaration fields from raw OCR text.
    """
    return {
        "manufacturer_details": extract_manufacturer_details(ocr_text),
        "net_quantity": extract_net_quantity(ocr_text),
        "mrp": extract_mrp(ocr_text),
        "manufacture_date": extract_manufacture_date(ocr_text),
        "customer_care": extract_customer_care(ocr_text),
        "fssai_license": extract_fssai_license(ocr_text),
        "country_of_origin": extract_country_of_origin(ocr_text),
    }
