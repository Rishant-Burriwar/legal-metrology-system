"""
Product Intelligence Service Orchestrator
=========================================

Integrates ingredient parsing, additive decoding, allergen analysis, and nutritional
panel detection into a unified, evidence-based product composition profile.
"""

from typing import Dict, Any, List, Optional
from app.product_intelligence.ingredient_extractor import (
    extract_ingredients_section,
    detect_nutritional_panel,
)
from app.product_intelligence.additive_decoder import decode_additives_from_text
from app.product_intelligence.allergen_detector import detect_allergens


def analyze_product_intelligence(
    combined_ocr_text: str,
    gemini_service: Optional[Any] = None,
    image_bytes_list: Optional[List[bytes]] = None,
) -> Dict[str, Any]:
    """
    Execute comprehensive secondary product intelligence analysis.
    Operates offline deterministically with optional Gemini multimodal enhancement.
    """
    # 1. Ingredient list extraction
    ing_res = extract_ingredients_section(combined_ocr_text)
    ingredient_items = ing_res.get("items", [])

    # 2. Additive decoding via INS Knowledge Base
    additives = decode_additives_from_text(
        ocr_text=combined_ocr_text,
        ingredient_items=ingredient_items,
    )

    # 3. Allergen detection (explicit vs inferred)
    allergens = detect_allergens(
        ocr_text=combined_ocr_text,
        ingredient_items=ingredient_items,
    )

    # 4. Nutritional facts detection
    nutrition = detect_nutritional_panel(combined_ocr_text)

    # 5. Risk classification summary
    risk_summary = {
        "green": sum(1 for a in additives if a.get("risk_level") == "green"),
        "yellow": sum(1 for a in additives if a.get("risk_level") == "yellow"),
        "orange": sum(1 for a in additives if a.get("risk_level") == "orange"),
        "red": sum(1 for a in additives if a.get("risk_level") == "red"),
    }

    # 6. Overall intelligence confidence
    base_conf = 0.85 if ing_res.get("found") else 0.60
    if additives:
        base_conf = min(0.96, base_conf + 0.08)
    if allergens:
        base_conf = min(0.98, base_conf + 0.04)

    return {
        "ingredients_found": ing_res.get("found", False),
        "raw_ingredient_text": ing_res.get("raw_text", ""),
        "ingredients": ingredient_items,
        "total_ingredients_count": len(ingredient_items),
        "additives": additives,
        "total_additives_count": len(additives),
        "allergens": allergens,
        "total_allergens_count": len(allergens),
        "nutritional_panel": nutrition,
        "risk_summary": risk_summary,
        "evidence_confidence": round(base_conf, 2),
        "disclaimer": (
            "Product Intelligence is strictly informational, intended to decode declared additives and statutory "
            "ingredients. Final statutory and legal metrology enforcement decisions remain with authorized officials."
        ),
    }


class ProductIntelligenceService:
    @staticmethod
    def analyze_package(
        ocr_text: str,
        gemini_service: Optional[Any] = None,
        image_bytes_list: Optional[List[bytes]] = None,
        is_food: bool = True,
    ) -> Dict[str, Any]:
        return analyze_product_intelligence(
            combined_ocr_text=ocr_text,
            gemini_service=gemini_service,
            image_bytes_list=image_bytes_list,
        )

