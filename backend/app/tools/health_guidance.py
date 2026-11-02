from typing import Dict, Any, Optional

EVIDENCE_BASED_GUIDANCE = {
    "Satisfactory": {
        "general_guidance": "Air quality is considered satisfactory, and air pollution poses little or no risk.",
        "vulnerable_populations": "No special precautions needed. Safe for outdoor activities.",
        "outdoor_activities": "Normal outdoor exercise, sports, and ventilation are fully encouraged.",
        "indoor_precautions": "Natural ventilation is safe and recommended during low-traffic hours.",
        "authoritative_sources": ["WHO Air Quality Guidelines 2021", "US EPA Air Quality Index Standards"]
    },
    "Moderate": {
        "general_guidance": "Air quality is acceptable; however, a small number of unusually sensitive individuals may experience minor respiratory symptoms.",
        "vulnerable_populations": "Individuals with pre-existing asthma, chronic bronchitis, or cardiovascular illness should monitor for shortness of breath or cough during exertion.",
        "outdoor_activities": "General public can engage in regular outdoor activities. Sensitive individuals should consider reducing prolonged or heavy outdoor exertion.",
        "indoor_precautions": "Ensure indoor air filters are clean. Normal room ventilation is acceptable.",
        "authoritative_sources": ["WHO Air Quality Guidelines", "US EPA AirNow Guidelines"]
    },
    "Poor": {
        "general_guidance": "Air quality may cause breathing discomfort to people with prolonged exposure, and heightened discomfort to those with heart and lung disease.",
        "vulnerable_populations": "Children, the elderly, and individuals with respiratory/cardiac conditions should substantially reduce heavy outdoor exertion.",
        "outdoor_activities": "Reschedule high-intensity outdoor training to indoor facilities. General public should take more breaks during outdoor physical activities.",
        "indoor_precautions": "Keep windows closed during peak traffic hours. Consider using standalone HEPA air purifiers.",
        "authoritative_sources": ["CPCB National Air Quality Index Criteria", "US EPA Health Advisories"]
    },
    "Very Poor": {
        "general_guidance": "Respiratory illness likely upon prolonged exposure. Healthy people may begin to experience adverse symptoms; serious effects on sensitive populations.",
        "vulnerable_populations": "Sensitive groups must avoid outdoor physical activity and remain indoors. Keep emergency inhalers and medications immediately accessible.",
        "outdoor_activities": "Avoid prolonged outdoor exertion. Wear well-fitted N95 / FFP2 particulate respirators if outdoor travel is unavoidable.",
        "indoor_precautions": "Seal doors and windows. Run HEPA filtration systems continuously on recirculating mode.",
        "authoritative_sources": ["WHO Global Air Quality Guidelines", "American Lung Association Advisory"]
    },
    "Severe": {
        "general_guidance": "Health emergency alert: everyone is more likely to be affected. Serious cardiovascular and respiratory impacts across the general population.",
        "vulnerable_populations": "Strict indoor confinement recommended. Vulnerable individuals should avoid physical exertion completely and consult physicians if symptoms exacerbate.",
        "outdoor_activities": "All outdoor physical activity should be avoided. Restrict transit to essential trips only with certified particulate respirator masks.",
        "indoor_precautions": "Operate high-efficiency particulate air filtration. Avoid indoor combustion (candles, incense, unvented heaters).",
        "authoritative_sources": ["WHO Health Crisis Thresholds", "US EPA Emergency Air Protection Guidance"]
    }
}

def get_health_guidance(category: str, dominant_pollutant: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve cautious, evidence-based environmental health and exposure guidance.
    Tailored to air quality categories with specific recommendations for vulnerable groups.
    Never provides clinical or diagnostic advice.
    """
    normalized_cat = "Satisfactory"
    for cat in EVIDENCE_BASED_GUIDANCE.keys():
        if cat.lower() == str(category).lower().strip():
            normalized_cat = cat
            break

    guidance = EVIDENCE_BASED_GUIDANCE[normalized_cat]

    disclaimer = (
        "Medical Disclaimer: GreenAir provides general environmental health advisories based on international air quality standards. "
        "This information is strictly educational and does not constitute individual medical diagnosis or treatment advice. "
        "Consult certified healthcare professionals and local public health authorities for medical evaluations."
    )

    pollutant_note = ""
    if dominant_pollutant:
        if dominant_pollutant.upper() == "PM2.5":
            pollutant_note = "Elevated PM2.5 requires particular attention to particulate filtration (HEPA / N95) due to its ability to enter deep alveoli and the bloodstream."
        elif dominant_pollutant.upper() == "O3":
            pollutant_note = "Ground-level ozone peaks during sunny afternoon hours. Scheduling outdoor activities for early mornings reduces ozone exposure."
        elif dominant_pollutant.upper() == "NO2":
            pollutant_note = "Elevated NO2 is tightly coupled with heavy traffic corridors. Maintain physical distance from congested arterial roadways."

    return {
        "category": normalized_cat,
        "dominant_pollutant": dominant_pollutant,
        "general_guidance": guidance["general_guidance"],
        "vulnerable_populations": guidance["vulnerable_populations"],
        "outdoor_activities": guidance["outdoor_activities"],
        "indoor_precautions": guidance["indoor_precautions"],
        "pollutant_specific_note": pollutant_note,
        "authoritative_sources": guidance["authoritative_sources"],
        "disclaimer": disclaimer
    }
