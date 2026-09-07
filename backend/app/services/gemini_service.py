"""
Gemini AI Multimodal Vision Service for Legal Metrology System.
===============================================================

Handles:
  1. Packaging Image Quality & Visual Analysis (glare, blur, curvature, surface reflections, packaging type).
  2. Direct Statutory Declaration Text Extraction (Rules LM-01 through LM-07).
  3. Hybrid Consensus Fusion between Gemini AI and Local OpenCV + EasyOCR.
  4. Automatic model fallback (gemini-3.5-flash-lite -> gemini-3.5-flash -> gemini-3.6-flash).
"""

import os
import re
import json
import base64
import logging
from typing import Dict, Any, Optional, Tuple, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = (
            api_key
            or os.getenv("GCP_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or getattr(settings, "GCP_API_KEY", "")
            or getattr(settings, "GEMINI_API_KEY", "")
        )
        self.model = model or settings.GEMINI_MODEL
        self.fallback_model = fallback_model or settings.GEMINI_FALLBACK_MODEL
        self.timeout = timeout or settings.GEMINI_TIMEOUT

    @property
    def is_configured(self) -> bool:
        """Check if a non-empty API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def _get_image_mime(self, image_bytes: bytes) -> str:
        """Infer MIME type from image magic bytes."""
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
            return "image/webp"
        return "image/png"

    def _call_gemini_api(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        model_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Execute synchronous HTTP request to Gemini Generative Language API.
        Attempts primary model first, falls back to secondary model on 404/503.
        """
        if not self.is_configured:
            logger.warning("Gemini API key is not configured.")
            return None

        target_model = model_name or self.model
        models_to_try = [target_model]
        if self.fallback_model and self.fallback_model != target_model:
            models_to_try.append(self.fallback_model)
        if "gemini-3.6-flash" not in models_to_try:
            models_to_try.append("gemini-3.6-flash")

        parts: List[Dict[str, Any]] = [{"text": prompt}]
        if image_bytes:
            mime = self._get_image_mime(image_bytes)
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": mime,
                    "data": b64_data,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }

        last_err = None
        for mod in models_to_try:
            url = f"{GEMINI_BASE_URL}/{mod}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = [p.get("text", "") for p in content_parts if "text" in p]
                        return "".join(text_parts).strip()
                elif resp.status_code == 404:
                    logger.warning(f"Gemini model {mod} returned 404, trying next model...")
                    continue
                else:
                    logger.warning(f"Gemini API ({mod}) returned {resp.status_code}: {resp.text[:200]}")
                    last_err = f"HTTP {resp.status_code}"
            except Exception as e:
                logger.warning(f"Gemini request ({mod}) failed: {e}")
                last_err = str(e)

        logger.error(f"All Gemini models failed. Last error: {last_err}")
        return None

    async def _call_gemini_api_async(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        model_name: Optional[str] = None,
    ) -> Optional[str]:
        """Asynchronous version of Gemini API request using httpx.AsyncClient."""
        if not self.is_configured:
            return None

        target_model = model_name or self.model
        models_to_try = [target_model]
        if self.fallback_model and self.fallback_model != target_model:
            models_to_try.append(self.fallback_model)
        if "gemini-3.6-flash" not in models_to_try:
            models_to_try.append("gemini-3.6-flash")

        parts: List[Dict[str, Any]] = [{"text": prompt}]
        if image_bytes:
            mime = self._get_image_mime(image_bytes)
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": mime,
                    "data": b64_data,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }

        for mod in models_to_try:
            url = f"{GEMINI_BASE_URL}/{mod}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = [p.get("text", "") for p in content_parts if "text" in p]
                        return "".join(text_parts).strip()
                elif resp.status_code == 404:
                    continue
                else:
                    logger.warning(f"Async Gemini ({mod}) returned {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Async Gemini ({mod}) failed: {e}")

        return None

    def _parse_json_markdown(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON enclosed in ```json ... ``` or raw JSON."""
        if not raw_text:
            return None
        text = raw_text.strip()
        # Strip markdown fences
        if "```json" in text:
            match = re.search(r"```json\s*(.+?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        elif "```" in text:
            match = re.search(r"```\s*(.+?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        try:
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse Gemini JSON output: {e}. Raw text snippet: {text[:200]}")
            return None

    def analyze_packaging_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Multimodal Visual Packaging Analysis:
        Inspects the packaging photo from a computer vision & regulatory inspector perspective:
          - Packaging surface type & material (pouch, foil, carton, can, bottle)
          - Surface defects (glare, harsh reflections, folds, curvature, shadows)
          - Legibility score (0–100)
          - Label completeness (full view vs cropped/truncated)
          - Recommended OpenCV filter / variant
          - Practical suggestions for the packaging auditor
        """
        prompt = """
You are a senior Computer Vision & Packaging Inspection Specialist auditing packaged commodities under India's Legal Metrology (Packaged Commodities) Rules, 2011.
Analyze this product packaging photo carefully from an image processing and label audit perspective.

Return ONLY a JSON object with this exact structure:
{
  "packaging_type": "<carton / metallic foil wrapper / flexible pouch / tin can / plastic bottle / glass jar / paper pack / unknown>",
  "legibility_score": <integer from 0 to 100>,
  "visual_clarity": "<Excellent / Good / Fair / Poor>",
  "lighting_condition": "<Balanced / Overexposed / Underexposed / Uneven Lighting>",
  "glare_detected": <true or false>,
  "glare_severity": "<None / Mild / Moderate / Severe>",
  "surface_curvature": "<Flat / Slight Curvature / Severe Curvature / Wrinkled Foil>",
  "is_truncated": <true or false, whether key label parts are cut off at the edges>,
  "recommended_opencv_variant": "<variant_a (Balanced) / variant_b (Illumination Normalized) / variant_c (Upscaled) / variant_d (Adaptive Binary) / variant_f (Inverted) / variant_g (Top-Hat Embossed)>",
  "visual_observations": [
    "<short observation about contrast, focus, or packaging condition>",
    "<short observation about text readability or reflective glare>"
  ],
  "inspector_recommendations": [
    "<practical tip for capturing better photos if any issues exist>"
  ]
}
"""
        raw_output = self._call_gemini_api(prompt, image_bytes=image_bytes)
        parsed = self._parse_json_markdown(raw_output)

        if not parsed:
            # Fallback heuristic defaults
            return {
                "packaging_type": "Packaged Commodity",
                "legibility_score": 85,
                "visual_clarity": "Good",
                "lighting_condition": "Balanced",
                "glare_detected": False,
                "glare_severity": "None",
                "surface_curvature": "Flat",
                "is_truncated": False,
                "recommended_opencv_variant": "variant_a",
                "visual_observations": ["Label image ingested successfully."],
                "inspector_recommendations": ["Ensure even lighting without flash glare."],
                "source": "fallback",
            }

        parsed["source"] = "gemini_multimodal_vision"
        return parsed

    def extract_statutory_fields(
        self,
        image_bytes: bytes,
        is_food_product: bool = True,
    ) -> Dict[str, Any]:
        """
        Multimodal OCR and Direct Statutory Declaration Extraction:
        Reads all text from the packaging image and structures it strictly according to:
          - LM-01: Manufacturer / Packer / Importer Name & Full Address (Rule 6(1)(a))
          - LM-02: Net Quantity in Standard Metric Units (Rule 6(1)(b) & Rule 12)
          - LM-03: Maximum Retail Price (MRP) with explicit check for 'incl. of all taxes' (Rule 6(1)(e))
          - LM-04: Month & Year of Manufacture / Packing (Rule 6(1)(d))
          - LM-05: Consumer Care Details (Phone / Email / Address) (Rule 6(1)(n))
          - LM-06: 14-digit FSSAI License Number for food commodities
          - LM-07: Country of Origin declaration
        """
        food_instruction = "This is a FOOD product. Look carefully for the 14-digit FSSAI license number (often near the FSSAI logo or license text)." if is_food_product else "This is a NON-FOOD product. FSSAI license is optional/not required."

        prompt = f"""
You are an expert AI Legal Metrology Auditor specializing in India's Legal Metrology (Packaged Commodities) Rules, 2011.
Carefully examine this packaging image. Extract ALL visible text verbatim, and identify the mandatory statutory declarations.
{food_instruction}

Pay critical attention to:
1. Manufacturer / Packer Details: Full company name and postal address.
2. Net Quantity: Number + standard metric unit (e.g., '250 g', '500 ml', '1 kg', '10 N', '5 pcs').
3. Maximum Retail Price (MRP): Identify the numeric price AND whether the mandatory phrase "inclusive of all taxes" or "incl. of all taxes" is present.
4. Month & Year of Manufacture/Packing: Look for 'Mfg Date', 'PKD', 'Date of Pkg', 'Best Before', or dates in MM/YYYY format.
5. Consumer Care Details: Customer care phone number, toll-free number, and email address.
6. FSSAI License: Exactly 14 digits (e.g., '10015011000234').
7. Country of Origin: 'Made in India', 'Country of Origin: India', etc.

Return ONLY a JSON object with this exact schema:
{{
  "verbatim_text": "<full transcribed text from the label with newlines preserving layout>",
  "fields": {{
    "manufacturer_name_and_address": "<full name and address text or null if missing>",
    "net_quantity_declared": "<e.g. 250 g or null if missing>",
    "mrp_declared_value": "<e.g. Rs. 85.00 or null if missing>",
    "mrp_numeric_amount": <float or null, e.g. 85.0>,
    "mrp_taxes_inclusive_declared": <true or false, true ONLY if 'incl. of all taxes' or similar is explicitly stated>,
    "mfg_month_and_year": "<e.g. 08/2026 or null if missing>",
    "customer_care_phone": "<e.g. 1800-112-4999 or null if missing>",
    "customer_care_email": "<e.g. care@suncrestfoods.in or null if missing>",
    "fssai_license_14_digit": "<exactly 14 digits or null if missing>",
    "country_of_origin": "<e.g. India or null if missing>"
  }},
  "overall_confidence": <float between 0.0 and 1.0>,
  "notes": "<any brief note about text clarity or ambiguous labels>"
}}
"""
        raw_output = self._call_gemini_api(prompt, image_bytes=image_bytes)
        parsed = self._parse_json_markdown(raw_output)

        if not parsed or "fields" not in parsed:
            logger.warning("Gemini field extraction returned empty or unparseable response.")
            return {
                "verbatim_text": "",
                "fields": self._empty_compliance_fields(),
                "confidence": 0.0,
                "notes": "Gemini extraction failed to parse response.",
                "success": False,
            }

        extracted_fields = self._format_gemini_fields_to_system_schema(
            parsed.get("fields", {}),
            raw_text=parsed.get("verbatim_text", ""),
            is_food_product=is_food_product,
        )

        return {
            "verbatim_text": parsed.get("verbatim_text", ""),
            "fields": extracted_fields,
            "confidence": float(parsed.get("overall_confidence", 0.95)),
            "notes": parsed.get("notes", ""),
            "success": True,
        }

    async def extract_statutory_fields_async(
        self,
        image_bytes: bytes,
        is_food_product: bool = True,
    ) -> Dict[str, Any]:
        """Asynchronous version of extract_statutory_fields."""
        food_instruction = "This is a FOOD product. Look carefully for the 14-digit FSSAI license number." if is_food_product else "This is a NON-FOOD product."
        prompt = f"""
You are an expert AI Legal Metrology Auditor specializing in India's Legal Metrology (Packaged Commodities) Rules, 2011.
Carefully examine this packaging image. Extract ALL visible text verbatim, and identify the mandatory statutory declarations.
{food_instruction}

Return ONLY a JSON object with this exact schema:
{{
  "verbatim_text": "<full transcribed text from the label with newlines>",
  "fields": {{
    "manufacturer_name_and_address": "<full name and address text or null if missing>",
    "net_quantity_declared": "<e.g. 250 g or null if missing>",
    "mrp_declared_value": "<e.g. Rs. 85.00 or null if missing>",
    "mrp_numeric_amount": <float or null, e.g. 85.0>,
    "mrp_taxes_inclusive_declared": <true or false>,
    "mfg_month_and_year": "<e.g. 08/2026 or null if missing>",
    "customer_care_phone": "<e.g. 1800-112-4999 or null if missing>",
    "customer_care_email": "<e.g. care@suncrestfoods.in or null if missing>",
    "fssai_license_14_digit": "<exactly 14 digits or null if missing>",
    "country_of_origin": "<e.g. India or null if missing>"
  }},
  "overall_confidence": <float between 0.0 and 1.0>,
  "notes": "<brief note>"
}}
"""
        raw_output = await self._call_gemini_api_async(prompt, image_bytes=image_bytes)
        parsed = self._parse_json_markdown(raw_output)

        if not parsed or "fields" not in parsed:
            return {
                "verbatim_text": "",
                "fields": self._empty_compliance_fields(),
                "confidence": 0.0,
                "notes": "Gemini async extraction unparseable.",
                "success": False,
            }

        extracted_fields = self._format_gemini_fields_to_system_schema(
            parsed.get("fields", {}),
            raw_text=parsed.get("verbatim_text", ""),
            is_food_product=is_food_product,
        )

        return {
            "verbatim_text": parsed.get("verbatim_text", ""),
            "fields": extracted_fields,
            "confidence": float(parsed.get("overall_confidence", 0.95)),
            "notes": parsed.get("notes", ""),
            "success": True,
        }

    def _format_gemini_fields_to_system_schema(
        self,
        g_fields: Dict[str, Any],
        raw_text: str = "",
        is_food_product: bool = True,
    ) -> Dict[str, Any]:
        """
        Translate Gemini's JSON fields into the exact schema expected by:
        app.rule_engine.rules.evaluate_compliance()
        """
        # 1. Manufacturer details
        mfr_raw = g_fields.get("manufacturer_name_and_address")
        if mfr_raw and str(mfr_raw).strip() and str(mfr_raw).strip().lower() != "null":
            mfr_val = str(mfr_raw).strip()
            status = "found" if len(mfr_val) >= 8 else "low_confidence"
            mfr_dict = {"value": mfr_val[:180], "status": status, "raw_snippet": mfr_val[:200], "source": "gemini"}
        else:
            mfr_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 2. Net quantity
        net_raw = g_fields.get("net_quantity_declared")
        if net_raw and str(net_raw).strip() and str(net_raw).strip().lower() != "null":
            net_val = str(net_raw).strip()
            # Standardize unit spacing e.g. "250g" -> "250 g"
            net_val = re.sub(r"(\d+)([a-zA-Z]+)", r"\1 \2", net_val)
            net_dict = {"value": net_val, "status": "found", "raw_snippet": net_val, "source": "gemini"}
        else:
            net_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 3. Maximum Retail Price (MRP)
        mrp_raw = g_fields.get("mrp_declared_value")
        taxes_incl = bool(g_fields.get("mrp_taxes_inclusive_declared", False))
        num_amount = g_fields.get("mrp_numeric_amount")

        if mrp_raw and str(mrp_raw).strip() and str(mrp_raw).strip().lower() != "null":
            clean_mrp = str(mrp_raw).strip()
            if not num_amount:
                # Extract numeric digits
                m_num = re.search(r"(\d+(?:\.\d{1,2})?)", clean_mrp)
                if m_num:
                    try:
                        num_amount = float(m_num.group(1))
                    except ValueError:
                        pass

            formatted_price = f"{num_amount:.2f}" if num_amount else clean_mrp
            tax_tag = " (incl. of all taxes)" if taxes_incl else " (taxes NOT declared)"
            disp_value = f"₹ {formatted_price}{tax_tag}"
            mrp_dict = {
                "value": disp_value,
                "amount": num_amount,
                "taxes_included": taxes_incl,
                "status": "found" if taxes_incl else "low_confidence",
                "raw_snippet": f"{clean_mrp}{tax_tag}",
                "source": "gemini",
            }
        else:
            mrp_dict = {"value": None, "amount": None, "taxes_included": False, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 4. Manufacturing Date
        mfg_raw = g_fields.get("mfg_month_and_year")
        if mfg_raw and str(mfg_raw).strip() and str(mfg_raw).strip().lower() != "null":
            mfg_val = str(mfg_raw).strip()
            mfg_dict = {"value": mfg_val, "status": "found", "raw_snippet": mfg_val, "source": "gemini"}
        else:
            mfg_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 5. Customer Care
        phone = g_fields.get("customer_care_phone")
        email = g_fields.get("customer_care_email")
        phone = str(phone).strip() if (phone and str(phone).lower() != "null") else None
        email = str(email).strip() if (email and str(email).lower() != "null") else None

        if phone and email:
            cc_val = f"Phone: {phone}, Email: {email}"
            cc_dict = {"value": cc_val, "phone": phone, "email": email, "status": "found", "raw_snippet": cc_val, "source": "gemini"}
        elif phone or email:
            cc_val = f"Phone: {phone}" if phone else f"Email: {email}"
            cc_dict = {"value": cc_val, "phone": phone, "email": email, "status": "low_confidence", "raw_snippet": cc_val, "source": "gemini"}
        else:
            cc_dict = {"value": None, "phone": None, "email": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 6. FSSAI License (14 digits)
        fssai_raw = g_fields.get("fssai_license_14_digit")
        if fssai_raw and str(fssai_raw).strip() and str(fssai_raw).strip().lower() != "null":
            digits_only = re.sub(r"\D", "", str(fssai_raw))
            if len(digits_only) == 14:
                fssai_dict = {"value": digits_only, "status": "found", "raw_snippet": digits_only, "source": "gemini"}
            elif len(digits_only) >= 10:
                fssai_dict = {"value": digits_only, "status": "low_confidence", "raw_snippet": digits_only, "source": "gemini"}
            else:
                fssai_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}
        else:
            fssai_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        # 7. Country of Origin
        coo_raw = g_fields.get("country_of_origin")
        if coo_raw and str(coo_raw).strip() and str(coo_raw).strip().lower() != "null":
            coo_val = str(coo_raw).strip().title()
            coo_dict = {"value": coo_val, "status": "found", "raw_snippet": coo_val, "source": "gemini"}
        else:
            coo_dict = {"value": None, "status": "not_found", "raw_snippet": None, "source": "gemini"}

        return {
            "manufacturer_details": mfr_dict,
            "net_quantity": net_dict,
            "mrp": mrp_dict,
            "manufacture_date": mfg_dict,
            "customer_care": cc_dict,
            "fssai_license": fssai_dict,
            "country_of_origin": coo_dict,
        }

    def _empty_compliance_fields(self) -> Dict[str, Any]:
        """Generate a baseline empty schema when extraction fails completely."""
        return {
            "manufacturer_details": {"value": None, "status": "not_found", "raw_snippet": None},
            "net_quantity": {"value": None, "status": "not_found", "raw_snippet": None},
            "mrp": {"value": None, "amount": None, "taxes_included": False, "status": "not_found", "raw_snippet": None},
            "manufacture_date": {"value": None, "status": "not_found", "raw_snippet": None},
            "customer_care": {"value": None, "phone": None, "email": None, "status": "not_found", "raw_snippet": None},
            "fssai_license": {"value": None, "status": "not_found", "raw_snippet": None},
            "country_of_origin": {"value": None, "status": "not_found", "raw_snippet": None},
        }

    def hybrid_consensus_merge(
        self,
        gemini_fields: Dict[str, Any],
        local_ocr_fields: Dict[str, Any],
        gemini_conf: float = 0.95,
        local_conf: float = 0.70,
    ) -> Dict[str, Any]:
        """
        Cross-Engine Consensus Fusion:
        Combines statutory field findings from Gemini Vision AI with local OpenCV+EasyOCR.

        Decision Matrix:
          - Both found with matching values -> "consensus_verified" (confidence boost)
          - Gemini found, local missed -> Gemini value adopted (source: "gemini")
          - Local found, Gemini missed -> Local value adopted (source: "local_ocr")
          - Both found with discrepancy -> Gemini preferred for small print/dense text, local retained in metadata.
        """
        status_rank = {"not_found": 0, "uncertain": 1, "low_confidence": 2, "found": 3}
        merged: Dict[str, Any] = {}
        consensus_log: Dict[str, Any] = {}

        field_names = [
            "manufacturer_details",
            "net_quantity",
            "mrp",
            "manufacture_date",
            "customer_care",
            "fssai_license",
            "country_of_origin",
        ]

        for fname in field_names:
            g_item = gemini_fields.get(fname, {"status": "not_found", "value": None})
            l_item = local_ocr_fields.get(fname, {"status": "not_found", "value": None})

            g_status = g_item.get("status", "not_found")
            l_status = l_item.get("status", "not_found")

            g_score = status_rank.get(g_status, 0)
            l_score = status_rank.get(l_status, 0)

            if g_score >= 2 and l_score >= 2:
                # Both detected the field! Check if values agree
                g_val = str(g_item.get("value", "")).lower()
                l_val = str(l_item.get("value", "")).lower()

                # Normalize strings for comparison
                g_norm = re.sub(r"[^a-z0-9]", "", g_val)
                l_norm = re.sub(r"[^a-z0-9]", "", l_val)

                is_agreement = (g_norm in l_norm) or (l_norm in g_norm) or (g_norm == l_norm)

                chosen = dict(g_item)
                chosen["consensus"] = "verified" if is_agreement else "gemini_preferred"
                chosen["cross_engine_validated"] = True
                chosen["local_detected_val"] = l_item.get("value")
                merged[fname] = chosen

                consensus_log[fname] = {
                    "status": "consensus_agreement" if is_agreement else "consensus_discrepancy_resolved",
                    "chosen_source": "gemini",
                    "gemini_val": g_item.get("value"),
                    "local_val": l_item.get("value"),
                }

            elif g_score > l_score:
                # Gemini found, local missed or uncertain
                chosen = dict(g_item)
                chosen["consensus"] = "gemini_exclusive"
                chosen["cross_engine_validated"] = False
                merged[fname] = chosen
                consensus_log[fname] = {
                    "status": "gemini_exclusive",
                    "chosen_source": "gemini",
                    "gemini_val": g_item.get("value"),
                }

            elif l_score > g_score:
                # Local found, Gemini missed
                chosen = dict(l_item)
                chosen["consensus"] = "local_exclusive"
                chosen["cross_engine_validated"] = False
                merged[fname] = chosen
                consensus_log[fname] = {
                    "status": "local_exclusive",
                    "chosen_source": "local_ocr",
                    "local_val": l_item.get("value"),
                }

            else:
                # Both missed or uncertain
                chosen = dict(g_item if g_score >= l_score else l_item)
                chosen["consensus"] = "none"
                chosen["cross_engine_validated"] = False
                merged[fname] = chosen
                consensus_log[fname] = {
                    "status": "not_detected",
                    "chosen_source": None,
                }

        merged["_consensus_metadata"] = {
            "engine": "hybrid_consensus",
            "gemini_confidence": round(gemini_conf, 3),
            "local_confidence": round(local_conf, 3),
            "fields_evaluated": len(field_names),
            "consensus_log": consensus_log,
        }

        return merged


# Singleton instance
_gemini_service = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
