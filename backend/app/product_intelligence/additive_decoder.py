"""
Additive Decoder Engine — Product Intelligence
==============================================

Extracts and decodes INS and E-number additive codes from package declarations
using an authoritative scientific knowledge base.
"""

import re
from typing import List, Dict, Any, Optional
from app.product_intelligence.additive_database import ADDITIVE_KNOWLEDGE_BASE, lookup_additive_by_token


def decode_additives_from_text(
    ocr_text: str,
    ingredient_items: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Search for INS / E-number additive codes and named additives in package text.
    Decodes each detected code into an evidence-based additive record.
    """
    detected_codes = set()
    decoded_additives = []

    # 1. Regex pattern for INS and E-numbers: e.g. "INS 322(i)", "INS-412", "E330", "INS 500(ii)"
    ins_pattern = re.compile(
        r"\b(?:INS|E)[\s\-\.]*(\d{3,4}(?:\([a-z0-9]+\)|[a-z])?)\b",
        re.IGNORECASE,
    )

    for match in ins_pattern.finditer(ocr_text):
        raw_code = match.group(0).upper().replace("-", " ")
        raw_code = " ".join(raw_code.split())
        num_part = match.group(1).lower()

        token_key = f"INS {num_part}"
        if token_key not in detected_codes:
            detected_codes.add(token_key)
            info = lookup_additive_by_token(raw_code) or lookup_additive_by_token(num_part)

            if info:
                decoded = dict(info)
                decoded["detected_token"] = raw_code
                decoded["is_recognized_in_kb"] = True
                decoded_additives.append(decoded)
            else:
                # Additive was declared on label, but is not in our top common database
                decoded_additives.append({
                    "identifier": raw_code,
                    "aliases": [raw_code],
                    "common_name": f"Permitted Food Additive ({raw_code})",
                    "function": "Additive (Unindexed Class)",
                    "purpose": "Declared statutory additive function per label formulation.",
                    "regulatory_status": "Declared under Codex/FSSAI nomenclature; verify specific maximum residue limits against current FSSAI schedules.",
                    "concerns": "Information based strictly on declared label token. Individual sensitivity may vary.",
                    "risk_level": "yellow",
                    "evidence_level": "Moderate",
                    "sources": ["Statutory Package Declaration", "Codex Class Names and the International Numbering System for Food Additives (CXG 36-1989)"],
                    "detected_token": raw_code,
                    "is_recognized_in_kb": False,
                })

    # 2. Check ingredient items for named additives (e.g., 'Citric Acid', 'Lecithin', 'Guar Gum', 'Sodium Benzoate')
    if ingredient_items:
        for item in ingredient_items:
            name = item.get("name", "")
            lower_name = name.lower()
            for known in ADDITIVE_KNOWLEDGE_BASE:
                if known["identifier"] not in detected_codes:
                    if known["common_name"].lower() in lower_name:
                        detected_codes.add(known["identifier"])
                        decoded = dict(known)
                        decoded["detected_token"] = name
                        decoded["is_recognized_in_kb"] = True
                        decoded_additives.append(decoded)

    return decoded_additives
