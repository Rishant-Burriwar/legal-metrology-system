from typing import Dict, Any, List, Tuple
from app.extraction.disambiguation import UNCERTAIN_TAG


def _attach_evidence(
    result: Dict[str, Any],
    field: Dict[str, Any],
    expected_condition: str,
) -> Dict[str, Any]:
    """Helper to attach visual evidence and statutory expectations to rule result."""
    val = field.get("value")
    result["detected_value"] = str(val) if val is not None else None
    result["expected_condition"] = expected_condition
    result["source_view"] = field.get("source_view") or "Front"
    result["evidence_image_path"] = field.get("evidence_image_path")
    result["bounding_box"] = field.get("bounding_box")
    result["confidence"] = float(field.get("confidence") or (0.95 if field.get("status") == "found" else (0.75 if field.get("status") == "low_confidence" else 0.0)))
    return result


def check_manufacturer_details(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("manufacturer_details", {})
    val = field.get("value")
    status = field.get("status")
    expected = "Complete name and address of the manufacturer, packer, or importer (Rule 6(1)(a))"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-01",
            "description": "Manufacturer details unreadable or uncertain [Rule 6(1)(a) — please upload a clearer image]",
            "severity": "Major",
            "status": "Fail",
        }
    elif status == "found" and val and len(val) >= 8:
        res = {
            "rule_code": "LM-01",
            "description": f"Manufacturer name and address declared: '{val[:60]}...'",
            "severity": "Major",
            "status": "Pass",
        }
    elif status == "low_confidence" and val:
        res = {
            "rule_code": "LM-01",
            "description": f"Manufacturer name detected with partial address: '{val[:60]}'",
            "severity": "Major",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-01",
            "description": "Manufacturer / Packer name or address missing or incomplete (Rule 6(1)(a))",
            "severity": "Major",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_net_quantity(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("net_quantity", {})
    val = field.get("value")
    status = field.get("status")
    expected = "Net quantity declared in standard metric units (g, kg, ml, l, count) (Rule 6(1)(b) & Rule 12)"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-02",
            "description": "Net quantity unreadable or uncertain [Rule 6(1)(b) — please upload a clearer image]",
            "severity": "Major",
            "status": "Fail",
        }
    elif status == "found" and val:
        res = {
            "rule_code": "LM-02",
            "description": f"Net quantity properly declared in standard metric unit: '{val}' (Rule 6(1)(b))",
            "severity": "Major",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-02",
            "description": "Net quantity missing or not in standard metric units (Rule 6(1)(b) & Rule 12)",
            "severity": "Major",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_mrp(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("mrp", {})
    val = field.get("value")
    status = field.get("status")
    taxes_included = field.get("taxes_included", False)
    expected = "Maximum Retail Price (MRP) in Indian Rupees inclusive of all taxes (Rule 6(1)(e))"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-03",
            "description": "MRP price unreadable or uncertain [Rule 6(1)(e) — please upload a clearer image]",
            "severity": "Major",
            "status": "Fail",
        }
    elif status == "found" and taxes_included:
        res = {
            "rule_code": "LM-03",
            "description": f"Maximum Retail Price declared with mandatory 'inclusive of all taxes': '{val}' (Rule 6(1)(e))",
            "severity": "Major",
            "status": "Pass",
        }
    elif val and not taxes_included:
        res = {
            "rule_code": "LM-03",
            "description": f"MRP amount present ({val}) but mandatory phrase 'inclusive of all taxes' is missing (Rule 6(1)(e))",
            "severity": "Major",
            "status": "Fail",
        }
    else:
        res = {
            "rule_code": "LM-03",
            "description": "Maximum Retail Price (MRP) declaration missing (Rule 6(1)(e))",
            "severity": "Major",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_manufacture_date(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("manufacture_date", {})
    val = field.get("value")
    status = field.get("status")
    expected = "Month and year of manufacture, packing, or import (MM/YYYY) (Rule 6(1)(d))"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-04",
            "description": "Manufacturing date unreadable or uncertain [Rule 6(1)(d) — please upload a clearer image]",
            "severity": "Major",
            "status": "Fail",
        }
    elif status in ("found", "low_confidence") and val:
        res = {
            "rule_code": "LM-04",
            "description": f"Month and year of manufacture / packing declared: '{val}' (Rule 6(1)(d))",
            "severity": "Major",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-04",
            "description": "Month and year of manufacture/packing/import missing (Rule 6(1)(d))",
            "severity": "Major",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_customer_care(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("customer_care", {})
    val = field.get("value")
    phone = field.get("phone")
    email = field.get("email")
    status = field.get("status")
    expected = "Consumer care contact details including telephone number and email address (Rule 6(1)(n))"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-05",
            "description": "Consumer care contact unreadable or uncertain [Rule 6(1)(n) — please upload a clearer image]",
            "severity": "Minor",
            "status": "Fail",
        }
    elif phone and email:
        res = {
            "rule_code": "LM-05",
            "description": f"Full consumer care details provided (Phone: {phone}, Email: {email}) (Rule 6(1)(n))",
            "severity": "Minor",
            "status": "Pass",
        }
    elif phone or email:
        channel = f"Phone ({phone})" if phone else f"Email ({email})"
        res = {
            "rule_code": "LM-05",
            "description": f"Partial consumer care provided: {channel}. Both phone and email are recommended (Rule 6(1)(n))",
            "severity": "Minor",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-05",
            "description": "Consumer care contact details (phone number and email address) missing (Rule 6(1)(n))",
            "severity": "Minor",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_fssai_license(data: Dict[str, Any], is_food_product: bool = True) -> Dict[str, Any]:
    field = data.get("fssai_license", {})
    val = field.get("value")
    status = field.get("status")
    expected = "14-digit FSSAI License/Registration Number for food commodities"

    if not is_food_product:
        res = {
            "rule_code": "LM-06",
            "description": "FSSAI license not applicable for non-food commodity category",
            "severity": "Major",
            "status": "Pass",
        }
    elif status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-06",
            "description": "FSSAI License 14-digit number unreadable or corrupted [Please upload a clearer image]",
            "severity": "Major",
            "status": "Fail",
        }
    elif status == "found" and val and len(val) == 14:
        res = {
            "rule_code": "LM-06",
            "description": f"Valid 14-digit FSSAI License Number declared: '{val}'",
            "severity": "Major",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-06",
            "description": "Mandatory 14-digit FSSAI License Number missing or invalid",
            "severity": "Major",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def check_country_of_origin(data: Dict[str, Any]) -> Dict[str, Any]:
    field = data.get("country_of_origin", {})
    val = field.get("value")
    status = field.get("status")
    expected = "Name of the country of origin / manufacture (Rule 6(1)(m))"

    if status == "uncertain" or val == UNCERTAIN_TAG:
        res = {
            "rule_code": "LM-07",
            "description": "Country of origin unreadable or uncertain [Please upload a clearer image]",
            "severity": "Minor",
            "status": "Fail",
        }
    elif status == "found" and val:
        res = {
            "rule_code": "LM-07",
            "description": f"Country of origin clearly stated: '{val}'",
            "severity": "Minor",
            "status": "Pass",
        }
    else:
        res = {
            "rule_code": "LM-07",
            "description": "Country of origin not clearly declared on the label",
            "severity": "Minor",
            "status": "Fail",
        }
    return _attach_evidence(res, field, expected)


def evaluate_compliance(
    extracted_data: Dict[str, Any],
    is_food_product: bool = True,
    compliance_threshold: float = 80.0,
) -> Tuple[float, str, List[Dict[str, Any]]]:
    """
    Run all 7 Legal Metrology validation rules with rich evidence attribution.
    Returns:
        (compliance_score, overall_status, violations_list)
    """
    validations = [
        check_manufacturer_details(extracted_data),
        check_net_quantity(extracted_data),
        check_mrp(extracted_data),
        check_manufacture_date(extracted_data),
        check_customer_care(extracted_data),
        check_fssai_license(extracted_data, is_food_product),
        check_country_of_origin(extracted_data),
    ]

    total_rules = len(validations)
    passed_rules = sum(1 for v in validations if v["status"] == "Pass")

    compliance_score = round((passed_rules / total_rules) * 100.0, 1)
    overall_status = "Compliant" if compliance_score >= compliance_threshold else "Non-Compliant"

    return compliance_score, overall_status, validations
