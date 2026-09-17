"""
Allergen Detection Engine — Product Intelligence
================================================

Detects major food allergens declared or inferred from packaging labels.
Strictly distinguishes between:
  1. Explicitly Declared Allergens (e.g., "Contains Soy, Milk" / "Allergen Advice:")
  2. Inferred Allergens (e.g., "Whey Solids -> Inferred Milk Allergen")
"""

import re
from typing import List, Dict, Any, Optional

ALLERGEN_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Milk": {
        "label": "Milk / Dairy",
        "keywords": ["milk", "dairy", "whey", "casein", "butter", "cheese", "cream", "lactose", "ghee", "milk solids"],
        "severity": "High",
    },
    "Soy": {
        "label": "Soy / Soybean",
        "keywords": ["soy", "soya", "soybean", "tofu", "soya lecithin", "soy lecithin"],
        "severity": "Moderate",
    },
    "Wheat": {
        "label": "Wheat / Gluten",
        "keywords": ["wheat", "gluten", "maida", "atta", "semolina", "barley", "rye", "oats", "malt"],
        "severity": "High",
    },
    "Peanuts": {
        "label": "Peanuts",
        "keywords": ["peanut", "groundnut", "monkey nut", "arachis"],
        "severity": "Critical",
    },
    "Tree Nuts": {
        "label": "Tree Nuts",
        "keywords": ["almond", "cashew", "walnut", "pistachio", "hazelnut", "pecan", "macadamia", "brazil nut"],
        "severity": "Critical",
    },
    "Egg": {
        "label": "Egg",
        "keywords": ["egg", "albumin", "ovalbumin", "egg powder", "egg yolk", "lysozyme"],
        "severity": "High",
    },
    "Fish": {
        "label": "Fish",
        "keywords": ["fish", "cod", "salmon", "tuna", "anchovy", "gelatin (fish)", "isinglass"],
        "severity": "High",
    },
    "Shellfish": {
        "label": "Crustacean & Shellfish",
        "keywords": ["shellfish", "crustacean", "shrimp", "prawn", "crab", "lobster", "mussel", "oyster", "clam"],
        "severity": "Critical",
    },
    "Sesame": {
        "label": "Sesame Seeds",
        "keywords": ["sesame", "tahini", "til"],
        "severity": "Moderate",
    },
    "Sulphites": {
        "label": "Sulphites (>10 mg/kg)",
        "keywords": ["sulphite", "sulfite", "sulfur dioxide", "sodium metabisulphite", "ins 220", "e220"],
        "severity": "Moderate",
    },
}


def detect_allergens(
    ocr_text: str,
    ingredient_items: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Audit packaging text for allergens.
    Differentiates explicit declarations from ingredients-inferred allergens.
    """
    detected_allergens: List[Dict[str, Any]] = []
    seen_allergens = set()

    # 1. Search for Explicit Allergen Declarations
    # e.g., "Contains: Milk, Soy", "Allergen advice: Contains wheat", "May contain traces of peanuts"
    explicit_pattern = re.compile(
        r"(?:Allergen\s*(?:Advice|Warning|Information)|Contains|May\s*Contain)[\s\:\-]+(.+?)(?=(?:Nutritional|Mfg|Best\s*Before|FSSAI|\n\n|\Z))",
        re.IGNORECASE,
    )

    explicit_match = explicit_pattern.search(ocr_text)
    explicit_snippet = explicit_match.group(0).strip() if explicit_match else ""

    if explicit_snippet:
        for allergen_name, meta in ALLERGEN_REGISTRY.items():
            for kw in meta["keywords"]:
                if re.search(rf"\b{re.escape(kw)}\b", explicit_snippet, re.IGNORECASE):
                    if allergen_name not in seen_allergens:
                        seen_allergens.add(allergen_name)
                        detected_allergens.append({
                            "name": allergen_name,
                            "allergen": allergen_name,
                            "display_name": meta["label"],
                            "type": "explicit",
                            "detection_type": "Explicitly Declared",
                            "is_explicit": True,
                            "trigger_keyword": kw,
                            "raw_snippet": explicit_snippet[:150],
                            "severity": meta["severity"],
                            "guidance": f"Explicitly listed by manufacturer. Sensitive consumers should avoid if allergic to {meta['label']}.",
                        })
                    break

    # 2. Search for Inferred Allergens from general ingredients list
    searchable_text = ocr_text.lower()
    if ingredient_items:
        searchable_text += " " + " ".join(item.get("name", "").lower() for item in ingredient_items)

    for allergen_name, meta in ALLERGEN_REGISTRY.items():
        if allergen_name in seen_allergens:
            continue
        for kw in meta["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b", searchable_text):
                seen_allergens.add(allergen_name)
                detected_allergens.append({
                    "name": allergen_name,
                    "allergen": allergen_name,
                    "display_name": meta["label"],
                    "type": "inferred",
                    "detection_type": "Potential Allergen (Inferred from ingredient list)",
                    "is_explicit": False,
                    "trigger_keyword": kw,
                    "raw_snippet": f"Identified from ingredient keyword '{kw}'",
                    "severity": meta["severity"],
                    "guidance": f"Not in dedicated allergen box, but inferred from presence of '{kw}'.",
                })
                break

    return detected_allergens
