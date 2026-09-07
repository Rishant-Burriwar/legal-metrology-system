import re
from typing import Optional, Tuple

UNCERTAIN_TAG = "[uncertain — please upload a clearer image]"

# Metric units recognized under Legal Metrology Rules
VALID_METRIC_UNITS = {
    "g", "gm", "gms", "gram", "grams",
    "kg", "kgs", "kilogram", "kilograms",
    "ml", "milli-litre", "millilitre", "millilitres", "milliliters",
    "l", "ltr", "litre", "litres", "liter", "liters",
    "pieces", "pcs", "units", "u", "n", "count"
}

# Canonical unit mappings
UNIT_CANONICAL = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "milli-litre": "ml", "millilitre": "ml", "millilitres": "ml", "milliliters": "ml",
    "l": "l", "ltr": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "pieces": "pcs", "pcs": "pcs", "units": "units", "u": "units", "n": "N", "count": "count",
}


def normalize_unit(unit_str: str) -> str:
    """Normalize a metric unit string to its canonical form."""
    lower = unit_str.strip().lower()
    return UNIT_CANONICAL.get(lower, lower)


def disambiguate_numeric_string(token: str) -> str:
    """
    Disambiguate ambiguous OCR characters inside an expected numeric string:
    - O, o -> 0
    - I, l, |, ! -> 1
    - S, s -> 5
    - B -> 8
    - Z, z -> 2
    - G -> 6
    - D -> 0 (in purely numeric context)
    - Comma as decimal separator in numbers (e.g. '25,50' -> '25.50')
    """
    cleaned = token.strip()

    # Replace comma between digits with period
    cleaned = re.sub(r"(\d),(\d)", r"\1.\2", cleaned)

    trans = str.maketrans({
        "O": "0", "o": "0",
        "I": "1", "l": "1", "|": "1", "!": "1",
        "S": "5", "s": "5",
        "B": "8",
        "Z": "2", "z": "2",
        "G": "6",
        "D": "0",
    })
    return cleaned.translate(trans)


def disambiguate_text_string(token: str) -> str:
    """
    Disambiguate numbers mistakingly inserted into alphabetic words
    and fix common OCR ligature/confusion errors.
    """
    # Fix specific common packaging word OCR misreadings
    word_fixes = {
        r"\b1NDIA\b": "INDIA",
        r"\bBHAR4T\b": "BHARAT",
        r"\bC0RPORATION\b": "CORPORATION",
        r"\bL1MITED\b": "LIMITED",
        r"\bPVT\.?\s*1TD\.?\b": "PVT. LTD.",
        r"\b1NDUSTRIES\b": "INDUSTRIES",
        r"\bF00DS\b": "FOODS",
        r"\bM4RKETED\b": "MARKETED",
        r"\bMFR\.?\b": "MFG.",
        r"\bPACKED\s+8Y\b": "PACKED BY",
        r"\bMFG\s+8Y\b": "MFG BY",
        # Additional common OCR misreadings for Indian packaging
        r"\bENTERPR1SES\b": "ENTERPRISES",
        r"\bPR0DUCTS\b": "PRODUCTS",
        r"\bQUAL1TY\b": "QUALITY",
        r"\bNUTR1TION\b": "NUTRITION",
        r"\bINGREDI[E3]NTS\b": "INGREDIENTS",
        r"\bN[E3]T\s*(?:W[E3]IGHT|QTY|QUANTITY)\b": "NET QUANTITY",
        r"\bM[A4]NUFACTURED\b": "MANUFACTURED",
        r"\bCONSUM[E3]R\b": "CONSUMER",
        r"\bCUST[O0]MER\b": "CUSTOMER",
        r"\bC[O0]UNTRY\b": "COUNTRY",
        r"\b[O0]RIGIN\b": "ORIGIN",
        r"\bIMP[O0]RTED\b": "IMPORTED",
        r"\bD[E3]CLARATION\b": "DECLARATION",
    }

    result = token
    for pattern, replacement in word_fixes.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Fix 'rn' -> 'm' ligature confusion (common in serif fonts)
    # Only apply in word context to avoid false positives
    rn_fixes = {
        r"\bgrarnrns?\b": "grams",
        r"\bgrarnrne?\b": "grams",
        r"\bnarne\b": "name",
        r"\bcomrnon\b": "common",
    }
    for pattern, replacement in rn_fixes.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def fix_unit_ocr_errors(unit_str: str) -> str:
    """Fix common OCR errors in unit strings."""
    fixes = {
        "q": "g",    # q misread as g
        "rnl": "ml",
        "rnL": "mL",
        "kq": "kg",
        "Kg": "kg",
        "KG": "kg",
        "GM": "gm",
        "Gm": "gm",
        "ML": "ml",
        "Lt": "l",
        "LT": "l",
        "Ltr": "ltr",
        "LTR": "ltr",
    }
    stripped = unit_str.strip()
    return fixes.get(stripped, stripped)


def validate_and_disambiguate_fssai(raw_str: str) -> Tuple[Optional[str], bool]:
    """
    Validate and disambiguate FSSAI 14-digit license number.
    Returns: (fssai_number_or_uncertain, is_valid)
    """
    if not raw_str:
        return None, False

    # Extract alphanumeric candidates near 'fssai' or 'lic'
    # Try numeric disambiguation on candidate
    candidate = disambiguate_numeric_string(raw_str)
    digits_only = re.sub(r"\D", "", candidate)

    if len(digits_only) == 14:
        # FSSAI numbers generally start with 1 or 2
        if digits_only[0] in ("1", "2"):
            return digits_only, True
        return digits_only, True

    # If it has 12-13 or 15 digits or contains high ambiguity
    if 10 <= len(digits_only) <= 16:
        return UNCERTAIN_TAG, False

    return None, False


def validate_and_disambiguate_net_quantity(raw_str: str) -> Tuple[Optional[str], bool]:
    """
    Disambiguate Net Quantity value and metric unit.
    E.g. '1OO g' -> '100 g', 'l.5 kg' -> '1.5 kg', '25O ml' -> '250 ml'.
    """
    if not raw_str:
        return None, False

    # Match number candidate followed by unit
    pattern = re.compile(
        r"([0-9OIl!sSBZzGD\.,]+)\s*([a-zA-Z]+)",
        re.IGNORECASE
    )
    match = pattern.search(raw_str)
    if not match:
        return None, False

    num_part = match.group(1)
    unit_part = fix_unit_ocr_errors(match.group(2))
    unit_lower = unit_part.lower()

    if unit_lower not in VALID_METRIC_UNITS:
        return None, False

    clean_num = disambiguate_numeric_string(num_part)
    # Check if clean_num is a valid positive float/int
    try:
        val = float(clean_num)
        if val <= 0:
            return UNCERTAIN_TAG, False
        # Normalize display (e.g. '100.0' -> '100' if integer)
        disp_num = str(int(val)) if val.is_integer() else str(val)
        canonical_unit = normalize_unit(unit_lower)
        return f"{disp_num} {canonical_unit}", True
    except ValueError:
        return UNCERTAIN_TAG, False


def validate_and_disambiguate_mrp(raw_str: str) -> Tuple[Optional[float], Optional[str], bool]:
    """
    Disambiguate MRP price amount.
    E.g. 'Rs. 2S.OO' -> 25.00, 'MRP: Rs. 1OO' -> 100.00.
    """
    if not raw_str:
        return None, None, False

    pattern = re.compile(r"(?:Rs\.?|INR|₹|MRP)?\s*([0-9OIl!sSBZzGD\.,]+)", re.IGNORECASE)
    match = pattern.search(raw_str)
    if not match:
        return None, None, False

    num_part = match.group(1)
    clean_num = disambiguate_numeric_string(num_part)

    try:
        amount = float(clean_num)
        if amount <= 0 or amount > 1000000:
            return None, UNCERTAIN_TAG, False
        return amount, f"{amount:.2f}", True
    except ValueError:
        return None, UNCERTAIN_TAG, False


def validate_and_disambiguate_date(raw_str: str) -> Tuple[Optional[str], bool]:
    """
    Disambiguate month/year or date string.
    E.g. '08/2O26' -> '08/2026', 'l2/25' -> '12/2025'.
    """
    if not raw_str:
        return None, False

    clean = disambiguate_numeric_string(raw_str)

    # DD/MM/YYYY or DD-MM-YYYY pattern
    dmy_pattern = re.compile(r"\b(0[1-9]|[12]\d|3[01])[\/\-\.](0[1-9]|1[0-2])[\/\-\.](20\d{2}|\d{2})\b")
    dmy_match = dmy_pattern.search(clean)
    if dmy_match:
        day = int(dmy_match.group(1))
        month = int(dmy_match.group(2))
        year_str = dmy_match.group(3)
        if len(year_str) == 2:
            year = 2000 + int(year_str)
        else:
            year = int(year_str)
        if 2015 <= year <= 2035 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day:02d}/{month:02d}/{year}", True

    # MM/YYYY or MM/YY pattern
    m_pattern = re.compile(r"\b(0[1-9]|1[0-2]|[1-9])[\/\-\.](20\d{2}|\d{2})\b")
    match = m_pattern.search(clean)
    if match:
        month = int(match.group(1))
        year_str = match.group(2)
        if len(year_str) == 2:
            year = 2000 + int(year_str)
        else:
            year = int(year_str)

        # Plausible packaging year range
        if 2015 <= year <= 2035 and 1 <= month <= 12:
            return f"{month:02d}/{year}", True

    # Check named month e.g. Aug 2026
    named_pattern = re.compile(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\/\-\.]+(20\d{2}|\d{2})\b",
        re.IGNORECASE
    )
    n_match = named_pattern.search(raw_str)
    if n_match:
        month_name = n_match.group(1).title()
        yr_str = disambiguate_numeric_string(n_match.group(2))
        yr = (2000 + int(yr_str)) if len(yr_str) == 2 else int(yr_str)
        if 2015 <= yr <= 2035:
            return f"{month_name} {yr}", True

    return None, False
