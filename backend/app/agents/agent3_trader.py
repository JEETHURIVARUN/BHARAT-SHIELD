import searoute as sr
import logging
import math
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── Asphaltene Instability Index (AII) ──────────────────────────────────────
# Based on the Colloidal Instability Index (CII) proxy method.
# Heavy penalty applies when blending two crudes with large API gravity delta.
# Industry threshold: API difference > 5° starts asphaltene precipitation risk.
AII_THRESHOLD_MILD   = 5.0   # API° apart — mild risk, small penalty
AII_THRESHOLD_SEVERE = 12.0  # API° apart — precipitation near-certain

def calculate_aii_penalty(
    crude_api: float,
    candidate_api: float,
    candidate_name: str = ""
) -> Dict[str, Any]:
    """
    Asphaltene Instability Index (AII) penalty calculator.
    Compares the target crude (or existing tank heel) API gravity against
    the candidate replacement crude's API gravity.

    Returns:
        aii_penalty   (float): penalty score added to Viability_Score
        aii_risk_band (str):   'NONE', 'MILD', 'MODERATE', 'SEVERE'
        aii_note      (str):   human-readable explanation
    """
    api_delta = abs(crude_api - candidate_api)

    if api_delta <= AII_THRESHOLD_MILD:
        return {
            "aii_penalty": 0.0,
            "aii_risk_band": "NONE",
            "api_delta": round(api_delta, 1),
            "aii_note": "Blend compatible — API delta within safe range."
        }
    elif api_delta <= AII_THRESHOLD_SEVERE:
        # Linear scale: 0 at threshold → 3.0 at severe threshold
        penalty = round(((api_delta - AII_THRESHOLD_MILD) / (AII_THRESHOLD_SEVERE - AII_THRESHOLD_MILD)) * 3.0, 2)
        return {
            "aii_penalty": penalty,
            "aii_risk_band": "MODERATE",
            "api_delta": round(api_delta, 1),
            "aii_note": (
                f"Moderate asphaltene risk (API Δ={round(api_delta,1)}°). "
                f"Blend ratio must stay <30% of {candidate_name or 'candidate'} "
                f"or asphaltene sludge may precipitate in crude distillation unit."
            )
        }
    else:
        # Severe: penalty scales further, capped at 8.0
        penalty = round(min(8.0, 3.0 + ((api_delta - AII_THRESHOLD_SEVERE) * 0.5)), 2)
        return {
            "aii_penalty": penalty,
            "aii_risk_band": "SEVERE",
            "api_delta": round(api_delta, 1),
            "aii_note": (
                f"SEVERE asphaltene incompatibility (API Δ={round(api_delta,1)}°). "
                f"Direct substitution NOT recommended — {candidate_name or 'this crude'} "
                f"will cause asphaltene precipitation, fouling distillation trays and "
                f"requiring emergency decoking. Estimated maintenance cost: $2-8M."
            )
        }


def calculate_maritime_route(
    origin_coords: list, dest_coords: list, avoid_chokepoints: list = None
) -> Dict[str, Any]:
    """
    Calculate maritime route and distance using the searoute python package.
    """
    options = {"units": "nm"}
    try:
        route = sr.searoute(origin_coords, dest_coords, **options)
        return {
            "distance_nm":    route['properties']['length'],
            "duration_hours": route['properties']['duration_hours'],
            "route_geometry": route['geometry']
        }
    except Exception as e:
        logger.error(f"Searoute calculation failed: {e}")
        return {}


def match_crude_assays(
    refinery_name: str,
    target_api: float,
    target_sulfur: float,
    target_tan: float,
    available_crudes: pd.DataFrame
) -> pd.DataFrame:
    """
    Match refinery metallurgy constraints with available global spot market crudes.
    Replacement Viability Score: Lower score = better match.
    
    Includes:
    - API Gravity delta
    - Sulfur content delta
    - TAN (acidity) delta
    - Freight cost
    - Route risk (geopolitical)
    - Asphaltene Instability Index (AII) penalty  [NEW — Upgrade 3]
    """
    weights = {
        "W1_API":    1.0,
        "W2_Sulfur": 1.0,
        "W3_TAN":    1.0,
        "W4_Freight":0.05,
        "W5_Risk":   0.1,
        "W6_AII":    2.5,   # AII penalty weight — significant chemical risk
    }

    # Per-refinery weight adjustments based on metallurgy configuration
    if refinery_name == "Paradip":
        weights["W3_TAN"]    = 0.2   # High TAN tolerance (IOCL configured)
        weights["W2_Sulfur"] = 0.5   # Tolerates sour up to 3.5%S
        weights["W6_AII"]    = 2.0   # Moderate blending flexibility
    elif refinery_name == "Jamnagar":
        weights["W1_API"]    = 0.2   # Tolerates ultra-heavy (16° API)
        weights["W2_Sulfur"] = 0.3   # Highest sulfur tolerance (5.0%S)
        weights["W6_AII"]    = 1.5   # High blending flexibility (world's largest)
    elif refinery_name == "MRPL":
        weights["W3_TAN"]    = 5.0   # STRICT low acid (max TAN 0.2)
        weights["W2_Sulfur"] = 3.0   # Strict low sulfur (max 1.5%S)
        weights["W6_AII"]    = 4.0   # Low blending tolerance — sweet crude refinery
    elif refinery_name == "Kochi":
        weights["W3_TAN"]    = 3.0
        weights["W2_Sulfur"] = 2.0
        weights["W6_AII"]    = 3.0
    elif refinery_name == "Bina":
        weights["W6_AII"]    = 2.5   # Designed for Omani crude — moderate tolerance

    df = available_crudes.copy()

    # Core property deltas
    df['Delta_API']    = np.abs(df['API']    - target_api)
    df['Delta_Sulfur'] = np.abs(df['Sulfur'] - target_sulfur)
    df['Delta_TAN']    = np.abs(df.get('TAN', pd.Series(0.1, index=df.index)) - target_tan)

    # Safe .get() with fallback for optional columns
    if 'Freight_Cost' not in df.columns:
        df['Freight_Cost'] = 15.0
    if 'Route_Risk' not in df.columns:
        df['Route_Risk'] = 0.5

    # Asphaltene Instability Index penalty [Upgrade 3]
    aii_results = df.apply(
        lambda row: calculate_aii_penalty(target_api, row['API'], row.get('Crude_Name', '')),
        axis=1
    )
    df['AII_Penalty']   = [r['aii_penalty']   for r in aii_results]
    df['AII_Risk_Band'] = [r['aii_risk_band'] for r in aii_results]
    df['AII_Note']      = [r['aii_note']       for r in aii_results]
    df['API_Delta']     = [r['api_delta']      for r in aii_results]

    df['Viability_Score'] = (
        weights["W1_API"]    * df['Delta_API']    +
        weights["W2_Sulfur"] * df['Delta_Sulfur'] +
        weights["W3_TAN"]    * df['Delta_TAN']    +
        weights["W4_Freight"]* df['Freight_Cost'] +
        weights["W5_Risk"]   * df['Route_Risk']   +
        weights["W6_AII"]    * df['AII_Penalty']
    )

    df = df.sort_values(by='Viability_Score', ascending=True).reset_index(drop=True)
    return df


if __name__ == "__main__":
    data = {
        'Crude_Name': ['Arab Light', 'Basrah Heavy', 'WTI', 'Merey (Venezuela)', 'Guyana Liza'],
        'API':    [33.0, 24.7, 39.6, 16.0, 32.1],
        'Sulfur': [1.77,  3.95, 0.24,  2.40,  0.50],
        'TAN':    [0.05,  0.50, 0.05,  0.30,  0.20],
        'Freight_Cost': [10.0, 12.0, 25.0, 30.0, 20.0],
        'Route_Risk':   [0.85,  0.88,  0.10,  0.40,  0.20],
    }
    df = pd.DataFrame(data)

    print("=== Paradip (32° API target) — Testing AII Scoring ===")
    result = match_crude_assays("Paradip", target_api=32.0, target_sulfur=1.5, target_tan=0.15, available_crudes=df)
    print(result[['Crude_Name', 'Viability_Score', 'AII_Penalty', 'AII_Risk_Band']].to_string())
    print()
    print("=== MRPL (35° API target, strict) — AII should be heavy penalty on Merey ===")
    result2 = match_crude_assays("MRPL", target_api=35.0, target_sulfur=0.5, target_tan=0.1, available_crudes=df)
    print(result2[['Crude_Name', 'Viability_Score', 'AII_Penalty', 'AII_Risk_Band']].to_string())
