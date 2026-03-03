"""
Prompt templates for Gemini news analysis.
"""

COMMODITY_ANALYSIS_PROMPT = """
Du bist ein erfahrener Rohstoff-Analyst. Analysiere den aktuellen Markt für {commodity_name} ({symbol}) und erstelle einen strukturierten Bericht auf Deutsch.

WICHTIGE REGELN:
1. ERFINDE NIEMALS Informationen, Daten, Termine oder Quellen
2. Wenn du etwas nicht weisst oder keine verlässlichen Daten findest: Sage "Keine verlässlichen Daten verfügbar"
3. Für TERMINE: Nur verifizierte, datierte Events aus offiziellen Quellen (z.B. OPEC, FED, EIA, USDA)
4. Wenn ein Termin unsicher ist, LASSE IHN WEG - lieber keine Termine als falsche
5. Alle Aussagen müssen durch die Google-Suchergebnisse belegt sein

Erstelle einen JSON-Bericht mit folgender Struktur:

{{
  "market_assessment": {{
    "summary": "Kurze Zusammenfassung der aktuellen Marktlage (2-3 Sätze)",
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0.0-1.0,
    "key_factors": ["Faktor 1", "Faktor 2", ...]
  }},
  "news_summary": "Zusammenfassung der wichtigsten aktuellen Nachrichten (3-4 Sätze)",
  "news_highlights": [
    "Highlight 1 mit Quellenangabe [1]",
    "Highlight 2 mit Quellenangabe [2]",
    ...
  ],
  "supply_demand": {{
    "supply_summary": "Angebotssituation (1-2 Sätze)",
    "demand_summary": "Nachfragesituation (1-2 Sätze)",
    "balance_outlook": "Ausblick auf Marktgleichgewicht"
  }},
  "macro_factors": {{
    "factors": ["USD-Entwicklung", "Zinspolitik", ...],
    "summary": "Zusammenfassung makroökonomischer Einflüsse"
  }},
  "upcoming_events": [
    {{
      "date": "YYYY-MM-DD oder 'Diese Woche'/'Nächste Woche'",
      "description": "Beschreibung des Events",
      "impact": "high" | "medium" | "low",
      "source": "Offizielle Quelle (z.B. EIA, FED, OPEC)"
    }}
  ]
}}

HINWEISE:
- Nummeriere Quellen im Text mit [1], [2], etc.
- Bewerte "sentiment" basierend auf der Gesamtlage
- "confidence" sollte die Sicherheit deiner Einschätzung widerspiegeln
- Bei "upcoming_events": NUR verifizierte Termine mit konkretem Datum
- Wenn keine Termine verfügbar: Leeres Array []

Antworte NUR mit dem JSON, ohne zusätzlichen Text.
"""


def get_commodity_analysis_prompt(symbol: str, commodity_name: str) -> str:
    """Generate the analysis prompt for a specific commodity."""
    return COMMODITY_ANALYSIS_PROMPT.format(
        symbol=symbol,
        commodity_name=commodity_name
    )


# Mapping of common commodity symbols to German names
COMMODITY_NAMES = {
    # Precious Metals
    "GC=F": "Gold",
    "SI=F": "Silber",
    "PL=F": "Platin",
    "PA=F": "Palladium",

    # Energy
    "CL=F": "Rohöl (WTI)",
    "BZ=F": "Brent Rohöl",
    "NG=F": "Erdgas",
    "HO=F": "Heizöl",
    "RB=F": "Benzin (RBOB)",

    # Agriculture - Grains
    "ZC=F": "Mais",
    "ZW=F": "Weizen",
    "ZS=F": "Sojabohnen",
    "ZM=F": "Sojaschrot",
    "ZL=F": "Sojaöl",
    "ZO=F": "Hafer",
    "ZR=F": "Reis",

    # Agriculture - Softs
    "KC=F": "Kaffee",
    "SB=F": "Zucker",
    "CC=F": "Kakao",
    "CT=F": "Baumwolle",
    "OJ=F": "Orangensaft",

    # Agriculture - Livestock
    "LE=F": "Lebendrind",
    "HE=F": "Magerschwein",
    "GF=F": "Mastrind",

    # Base Metals
    "HG=F": "Kupfer",
    "ALI=F": "Aluminium",

    # Indices (for reference)
    "DX=F": "US Dollar Index",
}


def get_commodity_name(symbol: str) -> str:
    """Get the German name for a commodity symbol."""
    return COMMODITY_NAMES.get(symbol, symbol)
