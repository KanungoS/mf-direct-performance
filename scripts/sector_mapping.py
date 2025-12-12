# sector_mapping.py
"""
Sector Theme Detection Module
---------------------------------
This module assigns sector themes to mutual fund schemes 
based on keywords found in scheme names.

Themes covered:
- Banking
- Pharma
- IT / Technology
- Infrastructure
- PSU
- Consumption
- Energy
- International
- ESG
- Diversified (fallback)
"""

SECTOR_KEYWORDS = {
    "Banking": [
        "bank", "financial services", "financial", "banking"
    ],
    "Pharma": [
        "pharma", "pharmaceutical", "healthcare", "health care", "life sciences"
    ],
    "IT": [
        "it", "technology", "tech", "information technology", "digital"
    ],
    "Infrastructure": [
        "infra", "infrastructure", "construction", "capex"
    ],
    "PSU": [
        "psu", "public sector", "govt", "government"
    ],
    "Consumption": [
        "consumption", "consumer", "fmcg", "discretionary"
    ],
    "Energy": [
        "energy", "power", "oil", "gas", "petro", "renewable"
    ],
    "International": [
        "global", "international", "us", "china", "japan", "europe", "world", "overseas"
    ],
    "ESG": [
        "esg", "sustainable", "responsible", "green"
    ]
}

def detect_sector_theme(name: str):
    """
    Detects sector theme using keywords.
    Returns one of the theme keys or 'Diversified'.
    """
    n = name.lower()

    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in n:
                return sector

    return "Diversified"
