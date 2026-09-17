"""
Ingredient & Composition Parser — Product Intelligence Engine
=============================================================

Parses raw OCR packaging text to:
  1. Detect ingredient sections ("Ingredients:", "Composition:", "Contains:").
  2. Split comma/semicolon/bullet-delimited ingredients while respecting nested parentheses.
  3. Detect presence of nutritional facts panel.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def split_ingredients_safely(text: str) -> List[str]:
    """
    Split ingredient string by comma, semicolon, or bullet points,
    ignoring commas that appear inside parentheses (e.g. 'Emulsifier (INS 322, INS 471)').
    """
    items = []
    current = []
    paren_depth = 0

    for char in text:
        if char in "([{":
            paren_depth += 1
            current.append(char)
        elif char in ")]}":
            paren_depth = max(0, paren_depth - 1)
            current.append(char)
        elif char in ",;•\n" and paren_depth == 0:
            token = "".join(current).strip()
            if token and len(token) > 1 and not token.lower().startswith("and "):
                items.append(token)
            current = []
        else:
            current.append(char)

    last_token = "".join(current).strip()
    if last_token and len(last_token) > 1:
        # Strip trailing period or disclaimer words
        last_token = re.sub(r"[\.\*]+$", "", last_token).strip()
        if last_token:
            items.append(last_token)

    return items


def extract_ingredients_section(ocr_text: str) -> Dict[str, Any]:
    """
    Locate and parse ingredient declaration section from packaging OCR text.
    """
    if not ocr_text:
        return {
            "found": False,
            "raw_text": "",
            "items": [],
            "source_section": None,
        }

    # Pattern to find start of ingredients section
    start_pattern = re.compile(
        r"(?:Ingredients|Composition|Ingr[eé]dients|Contains|Contents)[\s\:\-]+(.+?)(?=(?:Nutritional|Nutrition|Best\s*Before|Mfg|Manufactured|Net\s*Q|Customer|FSSAI|Country|Allergen\s*Info|\Z))",
        re.IGNORECASE | re.DOTALL,
    )

    match = start_pattern.search(ocr_text)
    if match:
        raw_section = match.group(1).strip()
        # Clean linebreaks
        clean_section = re.sub(r"\s+", " ", raw_section)
        # Limit runaway captures to 600 chars
        clean_section = clean_section[:600]

        raw_items = split_ingredients_safely(clean_section)
        structured_items = []

        for item in raw_items:
            clean_item = re.sub(r"^[\d\.\-\s]+", "", item).strip()
            if len(clean_item) < 2 or clean_item.lower() in ("and", "contains", "ingredients"):
                continue

            # Identify general ingredient category
            category = "Ingredient"
            lower = clean_item.lower()
            if re.search(r"\bins\s*\d+|\be\s*\d+|emulsifier|stabilizer|preservative|regulator|raising\s*agent|flavor", lower):
                category = "Food Additive"
            elif re.search(r"milk|soy|wheat|peanut|almond|cashew|egg|fish|sesame|gluten", lower):
                category = "Allergenic Ingredient"
            elif re.search(r"sugar|salt|oil|flour|cocoa|water|butter|syrup|spice", lower):
                category = "Primary Commodity"

            structured_items.append({
                "name": clean_item,
                "category": category,
            })

        return {
            "found": True,
            "raw_text": clean_section,
            "items": structured_items,
            "total_detected": len(structured_items),
        }

    # Fallback heuristic: check if common ingredient words exist
    common_keywords = ["sugar", "salt", "flour", "cocoa", "milk solids", "palm oil", "lecithin"]
    matched_words = [w for w in common_keywords if re.search(rf"\b{w}\b", ocr_text, re.IGNORECASE)]
    if len(matched_words) >= 2:
        items = [{"name": w.title(), "category": "Primary Commodity"} for w in matched_words]
        return {
            "found": True,
            "raw_text": f"Inferred from package terms: {', '.join(matched_words)}",
            "items": items,
            "total_detected": len(items),
        }

    return {
        "found": False,
        "raw_text": "",
        "items": [],
        "total_detected": 0,
    }


def detect_nutritional_panel(ocr_text: str) -> Dict[str, Any]:
    """Audit whether a statutory Nutritional Information panel is present on the package."""
    nutrition_patterns = [
        r"nutrition(?:al)?\s*(?:facts|information|values|panel)?",
        r"per\s*100\s*(?:g|ml)",
        r"energy\s*[:\s]*\d+\s*(?:kcal|kj)",
        r"protein\s*[:\s]*\d+",
        r"carbohydrate\s*[:\s]*\d+",
        r"total\s*fat\s*[:\s]*\d+",
    ]

    matches = 0
    detected_terms = []
    for pat in nutrition_patterns:
        m = re.search(pat, ocr_text, re.IGNORECASE)
        if m:
            matches += 1
            detected_terms.append(m.group(0).strip())

    has_panel = matches >= 2
    return {
        "detected": has_panel,
        "confidence": round(min(1.0, matches / 4.0), 2),
        "matched_elements": detected_terms,
        "status": "Verified Present" if has_panel else "Not Detected",
    }
