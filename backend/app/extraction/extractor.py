import re
from typing import Dict, Any, Optional
from app.extraction.disambiguation import (
    disambiguate_numeric_string,
    disambiguate_text_string,
    validate_and_disambiguate_fssai,
    validate_and_disambiguate_net_quantity,
    validate_and_disambiguate_mrp,
    validate_and_disambiguate_date,
    fix_unit_ocr_errors,
    normalize_unit,
    UNCERTAIN_TAG,
)


def clean_text_field(text: str) -> str:
    """Strip unnecessary whitespace and clean characters."""
    return re.sub(r"\s+", " ", text).strip()


def clean_and_validate_ocr_stream(raw_text: str) -> str:
    """
    Produce validated OCR text stream by applying contextual disambiguation
    to common words and packaging terms while preserving original layout.
    """
    if not raw_text:
        return ""
    lines = raw_text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned = disambiguate_text_string(line)
        cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


def extract_manufacturer_details(ocr_text: str) -> Dict[str, Any]:
    # Look for Manufactured by / Packed by / Marketed by / Imported by
    pattern = re.compile(
        r"(?:Mfg\b|Manufactured\s+by|Marketed\s+by|Packed\s+by|Imported\s+by|Pkd\s+by)[\s\:\-]+(.+?)(?=(?:MRP|Net\s*Q|Best\s*Before|Customer|FSSAI|Country|$))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(ocr_text)

    if match:
        raw_val = clean_text_field(disambiguate_text_string(match.group(1)))
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

    # Secondary heuristic: Look for company names with Ltd / Pvt / Works / Foods
    co_pattern = re.compile(
        r"([A-Z][A-Za-z0-9\s.,&-]+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Industries|Foods|Enterprises|Corporation)[^\n\r]*)",
        re.IGNORECASE,
    )
    co_match = co_pattern.search(ocr_text)
    if co_match:
        val = clean_text_field(disambiguate_text_string(co_match.group(1)))
        return {
            "value": val[:180],
            "status": "low_confidence",
            "raw_snippet": co_match.group(0)[:150],
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_net_quantity(ocr_text: str) -> Dict[str, Any]:
    # Match explicit "Net Quantity / Net Wt / Net Vol"
    explicit_pattern = re.compile(
        r"Net\s*(?:Quantity|Qty|Weight|Wt|Volume|Vol)[.:\s]*([0-9OIl!sSBZzG\.,]+\s*[a-zA-Z]+)",
        re.IGNORECASE,
    )
    exp_match = explicit_pattern.search(ocr_text)
    if exp_match:
        val, is_valid = validate_and_disambiguate_net_quantity(exp_match.group(1))
        if is_valid:
            return {
                "value": val,
                "status": "found",
                "raw_snippet": exp_match.group(0),
            }
        elif val == UNCERTAIN_TAG:
            return {
                "value": UNCERTAIN_TAG,
                "status": "uncertain",
                "raw_snippet": exp_match.group(0),
            }

    # General pattern with number + metric unit
    gen_pattern = re.compile(
        r"\b([0-9OIl!sSBZzG\.,]+\s*(?:kg|g|gm|gms|grams|ml|l|ltr|litres|liters|pieces|pcs|units|N|count))\b",
        re.IGNORECASE,
    )
    for m in gen_pattern.finditer(ocr_text):
        candidate = m.group(1)
        val, is_valid = validate_and_disambiguate_net_quantity(candidate)
        if is_valid:
            return {
                "value": val,
                "status": "found",
                "raw_snippet": m.group(0),
            }
        elif val == UNCERTAIN_TAG:
            return {
                "value": UNCERTAIN_TAG,
                "status": "uncertain",
                "raw_snippet": m.group(0),
            }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_mrp(ocr_text: str) -> Dict[str, Any]:
    # Look for MRP amount
    mrp_pattern = re.compile(
        r"(?:M\.?R\.?P\.?|MRP|Max\s*Retail\s*Price)[.:\s]*(?:Rs\.?|INR|₹)?\s*([0-9OIl!sSBZzG\.,]+)",
        re.IGNORECASE,
    )
    taxes_pattern = re.compile(
        r"(?:incl(?:usive)?\.?\s*(?:of)?\s*all\s*taxes|incl\.?\s*taxes)",
        re.IGNORECASE,
    )

    match = mrp_pattern.search(ocr_text)
    has_taxes_decl = bool(taxes_pattern.search(ocr_text))

    if match:
        raw_price_token = match.group(1)
        amount, formatted_price, is_valid = validate_and_disambiguate_mrp(raw_price_token)

        if not is_valid:
            return {
                "value": UNCERTAIN_TAG,
                "amount": None,
                "taxes_included": False,
                "status": "uncertain",
                "raw_snippet": match.group(0),
            }

        start_idx = max(0, match.start() - 20)
        end_idx = min(len(ocr_text), match.end() + 50)
        window = ocr_text[start_idx:end_idx]
        has_taxes_near = bool(taxes_pattern.search(window))

        taxes_ok = has_taxes_decl or has_taxes_near
        formatted_val = f"₹ {formatted_price}" + (" (incl. of all taxes)" if taxes_ok else " (taxes NOT declared)")

        return {
            "value": formatted_val,
            "amount": amount,
            "taxes_included": taxes_ok,
            "status": "found" if taxes_ok else "low_confidence",
            "raw_snippet": window.strip(),
        }

    # Backup: Look for standalone ₹ or Rs.
    price_pattern = re.compile(r"(?:Rs\.?|₹)\s*([0-9OIl!sSBZzG\.,]+)", re.IGNORECASE)
    p_match = price_pattern.search(ocr_text)
    if p_match:
        amount, formatted_price, is_valid = validate_and_disambiguate_mrp(p_match.group(1))
        if is_valid and amount is not None:
            return {
                "value": f"₹ {formatted_price} (unverified MRP tag)",
                "amount": amount,
                "taxes_included": False,
                "status": "low_confidence",
                "raw_snippet": p_match.group(0),
            }

    return {"value": None, "amount": None, "taxes_included": False, "status": "not_found", "raw_snippet": None}


def extract_manufacture_date(ocr_text: str) -> Dict[str, Any]:
    # Match patterns with keywords
    date_keyword_pattern = re.compile(
        r"(?:Mfg|Manufactured|Packed|Packing|Pkg|PKD|Mfd|Date|Dt)[.:\s]*(?:Date|Dt)?[:.\s]*([A-Za-z0-9\/\-\.\s]{3,15})",
        re.IGNORECASE,
    )
    match = date_keyword_pattern.search(ocr_text)
    if match:
        candidate = match.group(1).strip()
        val, is_valid = validate_and_disambiguate_date(candidate)
        if is_valid:
            return {
                "value": val,
                "status": "found",
                "raw_snippet": match.group(0),
            }

    # Generic month/year
    val, is_valid = validate_and_disambiguate_date(ocr_text)
    if is_valid:
        return {
            "value": val,
            "status": "low_confidence",
            "raw_snippet": val,
        }

    # If keyword was present but date was corrupt
    if match and len(match.group(1).strip()) >= 4:
        return {
            "value": UNCERTAIN_TAG,
            "status": "uncertain",
            "raw_snippet": match.group(0),
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_customer_care(ocr_text: str) -> Dict[str, Any]:
    phone_pattern = re.compile(
        r"(?:(?:Tel|Phone|Ph|Call|Helpline|Toll[\s\-]*Free|Care)[\s.:]*)?(1800[\s\-]*[0-9OIl!]{3}[\s\-]*[0-9OIl!]{3,4}|[6-9][0-9OIl!]{9}|\b[0-9OIl!]{3,5}[\-\s][0-9OIl!]{6,8}\b)",
        re.IGNORECASE,
    )
    email_pattern = re.compile(
        r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        re.IGNORECASE,
    )

    phone_match = phone_pattern.search(ocr_text)
    email_match = email_pattern.search(ocr_text)

    phone_val = None
    if phone_match:
        phone_disambiguated = disambiguate_numeric_string(phone_match.group(1))
        digits = re.sub(r"\D", "", phone_disambiguated)
        if len(digits) in (10, 11) or digits.startswith("1800"):
            phone_val = phone_disambiguated

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
    # Look for explicit FSSAI tag
    fssai_explicit = re.compile(
        r"(?:FSSAI|Lic(?:ense)?\.?\s*(?:No)?)[\s.:]*([A-Za-z0-9\s]{10,20})",
        re.IGNORECASE,
    )
    match = fssai_explicit.search(ocr_text)
    if match:
        val, is_valid = validate_and_disambiguate_fssai(match.group(1))
        if is_valid and val:
            return {
                "value": val,
                "status": "found",
                "raw_snippet": match.group(0),
            }
        elif val == UNCERTAIN_TAG:
            return {
                "value": UNCERTAIN_TAG,
                "status": "uncertain",
                "raw_snippet": match.group(0),
            }

    # Standalone 14-digit candidate
    val, is_valid = validate_and_disambiguate_fssai(ocr_text)
    if is_valid and val:
        return {
            "value": val,
            "status": "found",
            "raw_snippet": val,
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_country_of_origin(ocr_text: str) -> Dict[str, Any]:
    pattern = re.compile(
        r"(?:Country\s*of\s*Origin|Made\s*in|Product\s*of)[:\s]*([A-Za-z0-9\s]+?)(?=[\n,.]|$)",
        re.IGNORECASE,
    )
    match = pattern.search(ocr_text)
    if match:
        raw_country = disambiguate_text_string(match.group(1))
        country = clean_text_field(raw_country)
        if len(country) >= 3:
            return {
                "value": country.title(),
                "status": "found",
                "raw_snippet": match.group(0),
            }

    # Look for "Made in India" or "Origin: India"
    if re.search(r"\b(?:India|Bharat|1NDIA)\b", ocr_text, re.IGNORECASE):
        return {
            "value": "India",
            "status": "found",
            "raw_snippet": "India detected in label text",
        }

    return {"value": None, "status": "not_found", "raw_snippet": None}


def extract_compliance_fields(
    raw_ocr_text: str,
    validated_ocr_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract all 7 mandatory Legal Metrology declaration fields from OCR text.
    Uses validated OCR stream for precision extraction while falling back to raw.
    """
    primary_text = validated_ocr_text if validated_ocr_text else clean_and_validate_ocr_stream(raw_ocr_text)

    fields = {
        "manufacturer_details": extract_manufacturer_details(primary_text),
        "net_quantity": extract_net_quantity(primary_text),
        "mrp": extract_mrp(primary_text),
        "manufacture_date": extract_manufacture_date(primary_text),
        "customer_care": extract_customer_care(primary_text),
        "fssai_license": extract_fssai_license(primary_text),
        "country_of_origin": extract_country_of_origin(primary_text),
    }

    # If any crucial field is not found in primary_text, check raw_ocr_text as fallback
    if raw_ocr_text and raw_ocr_text != primary_text:
        if fields["mrp"]["status"] == "not_found":
            raw_mrp = extract_mrp(raw_ocr_text)
            if raw_mrp["status"] != "not_found":
                fields["mrp"] = raw_mrp

        if fields["fssai_license"]["status"] == "not_found":
            raw_fssai = extract_fssai_license(raw_ocr_text)
            if raw_fssai["status"] != "not_found":
                fields["fssai_license"] = raw_fssai

        if fields["net_quantity"]["status"] == "not_found":
            raw_net = extract_net_quantity(raw_ocr_text)
            if raw_net["status"] != "not_found":
                fields["net_quantity"] = raw_net

    return fields


# Status priority order (higher index = better)
_STATUS_PRIORITY = {
    "not_found": 0,
    "uncertain":  1,
    "low_confidence": 2,
    "found": 3,
}


def merge_multi_image_fields(
    all_extracted: list,
    all_ocr_confidences: list = None,
) -> Dict[str, Any]:
    """
    Merge extracted compliance fields from multiple images of the same product.

    When a label's information is spread across multiple photos (e.g., FSSAI on
    the back, manufacturing date on the side panel), this function picks the best
    result for each field across all images.

    Selection priority per field:
      found > low_confidence > uncertain > not_found

    When two or more images have the same status level for a field, the one from
    the image with the higher OCR confidence is preferred.

    Args:
        all_extracted:       List of extracted_data dicts, one per image.
        all_ocr_confidences: Optional list of per-image OCR confidence scores
                             (same length as all_extracted).

    Returns:
        Merged dict with the best field from each image, plus merge metadata.
    """
    if not all_extracted:
        return {}

    if len(all_extracted) == 1:
        result = dict(all_extracted[0])
        result["_merge_metadata"] = {
            "images_processed": 1,
            "merged": False,
        }
        return result

    # All field keys (union across all dicts to be safe)
    all_keys = set()
    for ext in all_extracted:
        all_keys.update(k for k in ext.keys() if not k.startswith("_"))

    merged: Dict[str, Any] = {}
    merge_log: Dict[str, Dict] = {}

    confidences = all_ocr_confidences or [0.5] * len(all_extracted)

    for field in all_keys:
        best_result = None
        best_status_score = -1
        best_conf = -1.0
        best_image_idx = -1

        for idx, ext_data in enumerate(all_extracted):
            field_result = ext_data.get(field)
            if field_result is None:
                continue

            status = field_result.get("status", "not_found")
            status_score = _STATUS_PRIORITY.get(status, 0)
            img_conf = confidences[idx] if idx < len(confidences) else 0.5

            # Higher status wins; tie-break by OCR confidence
            if (status_score > best_status_score) or (
                status_score == best_status_score and img_conf > best_conf
            ):
                best_result = field_result
                best_status_score = status_score
                best_conf = img_conf
                best_image_idx = idx

        if best_result is not None:
            merged[field] = best_result
            merge_log[field] = {
                "source_image_index": best_image_idx,
                "source_status": best_result.get("status"),
                "source_ocr_confidence": round(best_conf, 3),
            }

    # Append merge metadata (not sent to rule engine, only for logging/response)
    merged["_merge_metadata"] = {
        "images_processed": len(all_extracted),
        "merged": True,
        "field_sources": merge_log,
    }

    return merged
