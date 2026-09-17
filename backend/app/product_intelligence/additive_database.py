"""
Evidence-Based Food Additive Knowledge Base — Legal Metrology Product Intelligence
==================================================================================

Contains authoritative, evidence-backed scientific records for INS / E-number additives.
Does not make sensationalist or unverified health claims. All statements are grounded
in official food safety regulations (FSSAI, Codex Alimentarius, JECFA, EFSA).

Risk Levels:
  - green:  Generally permitted / low concern at standard regulated dietary levels
  - yellow: Requires context / individual sensitivity / quantity matters
  - orange: Potential concern requiring additional dietary context / ADI monitoring
  - red:    Strong evidence of significant concern, ban in specific jurisdictions, or strict limits
"""

from typing import Dict, Any, List, Optional

ADDITIVE_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "identifier": "INS 322",
        "aliases": ["322", "ins 322", "ins 322(i)", "e322", "lecithin", "soya lecithin", "soy lecithin"],
        "common_name": "Lecithin",
        "function": "Emulsifier & Antioxidant",
        "typical_use": "Confectionery, chocolates, baked goods, margarine",
        "purpose": "Helps blend oil- and water-based ingredients into a stable emulsion and prevents fat bloom in chocolate.",
        "regulatory_status": "Permitted in regulated food applications (FSSAI Food Safety & Standards, 2011; Codex STAN 192-1995).",
        "concerns": "Generally recognized as safe (GRAS). Derived primarily from soybeans or sunflower seeds; individuals with severe soy sensitivity should note origin.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Compendium of Food Safety and Standards (Food Product Standards and Additives)",
            "Codex Alimentarius GSFA (Class: Emulsifier)",
            "JECFA Toxicological Evaluation (No ADI limited needed)"
        ]
    },
    {
        "identifier": "INS 330",
        "aliases": ["330", "ins 330", "e330", "citric acid"],
        "common_name": "Citric Acid",
        "function": "Acidity Regulator & Antioxidant Synergist",
        "typical_use": "Beverages, jams, confectionery, processed foods",
        "purpose": "Maintains optimal pH, imparts pleasant tart taste, and inhibits oxidative discoloration.",
        "regulatory_status": "Permitted food additive under GMP (Good Manufacturing Practice) by FSSAI and Codex Alimentarius.",
        "concerns": "Naturally occurring organic acid. Low concern at normal food concentrations; frequent high-volume exposure can temporarily soften dental enamel.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Appendix A: List of Permitted Food Additives",
            "Codex Alimentarius Standard 192-1995 (Table 3: GMP)",
            "WHO Food Additives Series 5"
        ]
    },
    {
        "identifier": "INS 412",
        "aliases": ["412", "ins 412", "e412", "guar gum"],
        "common_name": "Guar Gum",
        "function": "Thickener & Stabilizer",
        "typical_use": "Ice creams, sauces, bakery products, dairy desserts",
        "purpose": "Improves texture, controls viscosity, and prevents ice crystal formation during frozen storage.",
        "regulatory_status": "Permitted food additive under FSSAI and Codex GMP provisions.",
        "concerns": "Naturally derived legume polysaccharide. High dietary fiber content; excessive intake may cause mild gastrointestinal bloating in sensitive individuals.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Food Safety and Standards (Food Products Standards) Regulations",
            "EFSA Panel on Food Additives Re-evaluation of Guar Gum (2017)",
            "Codex GSFA Table 3"
        ]
    },
    {
        "identifier": "INS 211",
        "aliases": ["211", "ins 211", "e211", "sodium benzoate"],
        "common_name": "Sodium Benzoate",
        "function": "Preservative (Antimicrobial)",
        "typical_use": "Carbonated soft drinks, fruit juices, pickles, acidic condiments",
        "purpose": "Inhibits growth of yeasts, bacteria, and molds in acidic food matrices.",
        "regulatory_status": "Permitted with strict maximum residue limits (FSSAI limits typically 100–120 ppm; Codex ADI: 0–5 mg/kg body weight).",
        "concerns": "Permitted preservative under regulated limits. In beverages containing ascorbic acid (Vitamin C) exposed to heat/light, trace benzene formation can occur, hence formulations are strictly monitored.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Food Additives Regulations (Table 2: Class II Preservatives)",
            "JECFA Evaluation: Acceptable Daily Intake 0–5 mg/kg bw",
            "US FDA Centre for Food Safety: Survey on Benzoate and Ascorbic Acid"
        ]
    },
    {
        "identifier": "INS 102",
        "aliases": ["102", "ins 102", "e102", "tartrazine", "fd&c yellow no. 5"],
        "common_name": "Tartrazine",
        "function": "Synthetic Food Color (Yellow)",
        "typical_use": "Flavored drinks, confectionery, dessert mixes, packaged snacks",
        "purpose": "Imparts stable lemon-yellow coloration to packaged food products.",
        "regulatory_status": "Permitted under FSSAI with mandatory label declaration and maximum limit of 100 mg/kg.",
        "concerns": "May trigger intolerance symptoms (hives, bronchoconstriction) in aspirin-sensitive individuals. Subject to statutory advisory warning labels in certain jurisdictions (EU Regulation 1333/2008).",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Mandatory Declarations for Synthetic Food Colors (Rule 2.4.5)",
            "EFSA Scientific Opinion on Tartrazine Re-evaluation (2009)",
            "Codex STAN 192-1995"
        ]
    },
    {
        "identifier": "INS 110",
        "aliases": ["110", "ins 110", "e110", "sunset yellow fcf", "fd&c yellow no. 6"],
        "common_name": "Sunset Yellow FCF",
        "function": "Synthetic Food Color (Orange)",
        "typical_use": "Orange sodas, confectionery, snack seasonings, dessert powders",
        "purpose": "Imparts reddish-yellow/orange tint to food commodities.",
        "regulatory_status": "Permitted under FSSAI with mandatory statutory declaration on the principal display panel.",
        "concerns": "Regulated synthetic azo dye with an ADI of 0–4 mg/kg bw. Rare allergic responses in sensitive individuals.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Food Safety and Standards Regulations, 2011",
            "JECFA 74th Meeting (2011) ADI Revision",
            "EFSA Re-evaluation of Sunset Yellow FCF (2014)"
        ]
    },
    {
        "identifier": "INS 150d",
        "aliases": ["150d", "ins 150d", "e150d", "caramel iv", "sulphite ammonia caramel"],
        "common_name": "Caramel IV (Sulfite Ammonia Caramel)",
        "function": "Food Color (Brown)",
        "typical_use": "Colas, gravies, confectioneries, dark sauces",
        "purpose": "Provides rich brown to black coloration in acidic beverage systems.",
        "regulatory_status": "Permitted under FSSAI with maximum limit on 4-MEI byproduct content (< 250 mg/kg).",
        "concerns": "Contains minor reaction byproducts (4-methylimidazole) which are regulated with strict upper safety limits by food safety authorities.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Food Product Standards Regulations",
            "EFSA Scientific Opinion on the Re-evaluation of Caramel Colours (2011)",
            "JECFA Food Additives Series 44"
        ]
    },
    {
        "identifier": "INS 621",
        "aliases": ["621", "ins 621", "e621", "msg", "monosodium glutamate"],
        "common_name": "Monosodium Glutamate (MSG)",
        "function": "Flavor Enhancer (Umami)",
        "typical_use": "Instant noodles, savory snacks, soups, seasoning blends",
        "purpose": "Enhances savory/umami taste perception via glutamate receptors on the tongue.",
        "regulatory_status": "Permitted in specific food categories under FSSAI with mandatory label declaration. Prohibited in foods meant for infants below 12 months.",
        "concerns": "Extensively evaluated food additive. While widely accepted as safe by scientific consensus (JECFA ADI not specified), transient sensitivity symptoms may occur in a small subset of the population when consumed in large boluses on an empty stomach.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Regulation on Flavor Enhancers and MSG Declarations",
            "JECFA 31st Report: Evaluation of Glutamates",
            "US FDA Questions and Answers on Monosodium Glutamate"
        ]
    },
    {
        "identifier": "INS 500(ii)",
        "aliases": ["500", "500(ii)", "ins 500", "ins 500(ii)", "ins 500ii", "e500", "sodium bicarbonate", "baking soda"],
        "common_name": "Sodium Bicarbonate",
        "function": "Raising Agent & Acidity Regulator",
        "typical_use": "Biscuits, cookies, cakes, wafer sheets, confectionery",
        "purpose": "Releases carbon dioxide gas during baking, giving biscuits and cakes porous, crisp texture.",
        "regulatory_status": "Permitted under GMP in baked goods and confectionery under FSSAI and Codex Alimentarius.",
        "concerns": "Simple mineral salt of low toxicological concern. Contributes to sodium intake in the overall diet.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Table 3: Additives permitted under GMP",
            "Codex GSFA Table 3",
            "EFSA Safety Assessment on Sodium Carbonates"
        ]
    },
    {
        "identifier": "INS 450",
        "aliases": ["450", "ins 450", "ins 450(i)", "e450", "diphosphates", "sodium acid pyrophosphate"],
        "common_name": "Diphosphates (Pyrophosphates)",
        "function": "Leavening Acid & Sequestrant",
        "typical_use": "Baking powders, processed cheese, processed meats",
        "purpose": "Acts as controlled slow-acting leavening acid to generate uniform aeration in doughs.",
        "regulatory_status": "Permitted with group maximum limits for phosphates (FSSAI / Codex limit: max 70 mg/kg bw as phosphorus).",
        "concerns": "Contributes to dietary phosphorus. High cumulative phosphate intake across highly processed foods may affect mineral balance in individuals with chronic kidney disease.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Standards for Leavening Agents",
            "EFSA Scientific Opinion on the Re-evaluation of Phosphoric Acid and Phosphates (2019)",
            "Codex STAN 192-1995"
        ]
    },
    {
        "identifier": "INS 202",
        "aliases": ["202", "ins 202", "e202", "potassium sorbate"],
        "common_name": "Potassium Sorbate",
        "function": "Preservative (Antifungal & Antibacterial)",
        "typical_use": "Bakery goods, jams, cheeses, beverages, dips",
        "purpose": "Prevents mold and yeast proliferation without affecting product pH or taste.",
        "regulatory_status": "Permitted Class II preservative under FSSAI regulations with category-specific maximum residue limits.",
        "concerns": "Extensively metabolized by fatty acid oxidation in the body. Very low toxicity profile; occasional skin contact sensitivity reported in topical uses.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Table on Permitted Preservatives",
            "JECFA Monograph on Sorbates (ADI 0–25 mg/kg bw)",
            "EFSA Opinion on Sorbates Re-evaluation (2015)"
        ]
    },
    {
        "identifier": "INS 282",
        "aliases": ["282", "ins 282", "e282", "calcium propionate"],
        "common_name": "Calcium Propionate",
        "function": "Preservative & Mold Inhibitor",
        "typical_use": "Sliced bread, bakery commodities, tortillas",
        "purpose": "Inhibits mold and rope-forming bacteria in grain-based products.",
        "regulatory_status": "Permitted under FSSAI for bread and bakery products (limit: 5000 ppm).",
        "concerns": "Metabolized as propionic acid (a normal byproduct of human gut flora). Safe at permitted levels; isolated case reports of behavioral irritability in children have not been replicated in large clinical trials.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Standards for Bakery Products",
            "EFSA Scientific Opinion on Propionic Acid and Propionates (2014)",
            "Codex GSFA Table 3"
        ]
    },
    {
        "identifier": "INS 471",
        "aliases": ["471", "ins 471", "e471", "mono- and diglycerides of fatty acids", "mono and diglycerides"],
        "common_name": "Mono- and Diglycerides of Fatty Acids",
        "function": "Emulsifier & Crumb Softener",
        "typical_use": "Breads, cakes, ice creams, margarine, whipped toppings",
        "purpose": "Extends bakery shelf life by delaying starch retrogradation (staling) and stabilizes fat-water emulsions.",
        "regulatory_status": "Permitted under GMP in most food categories by FSSAI and Codex.",
        "concerns": "Derived from plant or animal fats. Digested by normal lipid metabolism like natural fats. Vegans and vegetarians should note whether sourced from plant oils or animal fat.",
        "risk_level": "green",
        "evidence_level": "High",
        "sources": [
            "FSSAI Permitted Emulsifiers and Stabilizers",
            "JECFA Evaluation: ADI not limited",
            "Codex STAN 192-1995"
        ]
    },
    {
        "identifier": "INS 955",
        "aliases": ["955", "ins 955", "e955", "sucralose"],
        "common_name": "Sucralose",
        "function": "Non-Nutritive High-Intensity Sweetener",
        "typical_use": "Sugar-free beverages, tabletop sweeteners, dietary foods, chewing gums",
        "purpose": "Provides approx. 600× sweetness of table sugar without caloric load.",
        "regulatory_status": "Permitted under FSSAI with mandatory warning 'Contains Non-Caloric Sweetener' and product-specific limits.",
        "concerns": "Heat-stable chlorinated sucrose derivative. ADI established at 0–15 mg/kg bw. Excessive intake may alter gut microbiota composition in animal models.",
        "risk_level": "yellow",
        "evidence_level": "High",
        "sources": [
            "FSSAI Regulation 2.4.5 on Artificial Sweeteners",
            "JECFA ADI Evaluation (0–15 mg/kg bw)",
            "EFSA Scientific Opinion on Sucralose Safety"
        ]
    },
    {
        "identifier": "INS 951",
        "aliases": ["951", "ins 951", "e951", "aspartame"],
        "common_name": "Aspartame",
        "function": "Non-Nutritive Sweetener",
        "typical_use": "Diet sodas, sugar-free candies, yogurt, table sweeteners",
        "purpose": "Delivers intense sweetness (approx. 200× sucrose) with negligible calories.",
        "regulatory_status": "Permitted with mandatory statutory label warning: 'Contains Aspartame. Not recommended for phenylketonurics'.",
        "concerns": "Contains phenylalanine. Strictly contraindicated for individuals with Phenylketonuria (PKU). Classified by IARC as Group 2B (possibly carcinogenic to humans) with JECFA reaffirming ADI of 0–40 mg/kg bw based on current intake levels.",
        "risk_level": "orange",
        "evidence_level": "High",
        "sources": [
            "FSSAI Mandatory Statutory PKU Warning Declaration",
            "WHO / IARC & JECFA Joint Assessment of Aspartame (July 2023)",
            "EFSA Comprehensive Re-evaluation of Aspartame (2013)"
        ]
    },
    {
        "identifier": "INS 407",
        "aliases": ["407", "ins 407", "e407", "carrageenan"],
        "common_name": "Carrageenan",
        "function": "Gelling Agent & Stabilizer",
        "typical_use": "Plant-based milks, dairy desserts, deli meats, infant formulas",
        "purpose": "Forms clear gels, suspends cocoa particles, and provides creamy mouthfeel.",
        "regulatory_status": "Permitted under FSSAI and Codex. Prohibited in infant formula in the EU.",
        "concerns": "Extracted from red edible seaweeds. Food-grade carrageenan is distinct from degraded carrageenan (poligeenan). High concentrations have been studied for potential mild intestinal inflammatory effects in rodent models.",
        "risk_level": "yellow",
        "evidence_level": "Moderate",
        "sources": [
            "FSSAI Table 3 Permitted Stabilizers",
            "JECFA Evaluation on Carrageenan in Infant Formula (2014)",
            "EFSA Re-evaluation of Carrageenan (2018)"
        ]
    }
]


def lookup_additive_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Lookup an additive by INS number, code, or common name."""
    clean = token.strip().lower()
    # Normalize INS / E prefixes
    clean_normalized = clean.replace("e-", "e").replace("ins-", "ins ").replace("ins", "ins ").strip()
    clean_normalized = " ".join(clean_normalized.split())

    for item in ADDITIVE_KNOWLEDGE_BASE:
        for alias in item["aliases"]:
            if alias == clean or alias == clean_normalized:
                return item
            # Token substring match for INS numbers (e.g., '322' in 'ins 322')
            if clean.startswith("ins") and alias in clean:
                return item
    return None
