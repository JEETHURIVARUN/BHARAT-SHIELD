import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ─── LNG Terminal Database ────────────────────────────────────────────────────
LNG_TERMINALS = {
    "Dahej": {
        "operator": "Petronet LNG",
        "capacity_mmtpa": 17.5,
        "send_out_mmscmd": 24.0,
        "utilization_pct": 92.0,
        "coordinates": [72.5, 21.7],
        "pipeline": "HVJ",
        "accepts": ["Q-Flex", "Q-Max", "Standard"]
    },
    "Hazira": {
        "operator": "Shell/TPC",
        "capacity_mmtpa": 5.0,
        "send_out_mmscmd": 7.0,
        "utilization_pct": 78.0,
        "coordinates": [72.6, 21.1],
        "pipeline": "HVJ",
        "accepts": ["Standard"]
    },
    "Kochi": {
        "operator": "Petronet LNG",
        "capacity_mmtpa": 5.0,
        "send_out_mmscmd": 7.0,
        "utilization_pct": 35.0,
        "coordinates": [76.2, 10.0],
        "pipeline": "KKNPP",
        "accepts": ["Standard"]
    },
    "Dabhol": {
        "operator": "GAIL/RGPPL",
        "capacity_mmtpa": 5.0,
        "send_out_mmscmd": 6.5,
        "utilization_pct": 55.0,
        "coordinates": [73.1, 17.6],
        "pipeline": "MSEZ",
        "accepts": ["Standard"]
    },
    "Ennore": {
        "operator": "IOT/Indian Oil",
        "capacity_mmtpa": 5.0,
        "send_out_mmscmd": 7.0,
        "utilization_pct": 60.0,
        "coordinates": [80.3, 13.2],
        "pipeline": "RLNG Southeast",
        "accepts": ["Standard"]
    },
    "Mundra_LNG": {
        "operator": "GSPC/Swan Energy",
        "capacity_mmtpa": 5.0,
        "send_out_mmscmd": 6.0,
        "utilization_pct": 40.0,
        "coordinates": [69.7, 22.8],
        "pipeline": "GSPL",
        "accepts": ["Standard"]
    }
}

# ─── LNG Supplier Catalogue ──────────────────────────────────────────────────
LNG_SUPPLIERS = [
    {"name": "QatarEnergy RasGas",    "country": "Qatar",     "methane_pct": 91.5, "wobbe_index": 50.2, "gcv_mmbtu": 1085, "contract": "Long-term",  "route_risk": 0.85, "freight_day_rate": 85000,  "voyage_days": 18},
    {"name": "QatarEnergy Qatargas",  "country": "Qatar",     "methane_pct": 90.8, "wobbe_index": 49.8, "gcv_mmbtu": 1078, "contract": "Long-term",  "route_risk": 0.85, "freight_day_rate": 85000,  "voyage_days": 18},
    {"name": "Woodside Scarborough",  "country": "Australia", "methane_pct": 93.0, "wobbe_index": 51.0, "gcv_mmbtu": 1092, "contract": "Long-term",  "route_risk": 0.10, "freight_day_rate": 90000,  "voyage_days": 14},
    {"name": "Gorgon LNG",           "country": "Australia", "methane_pct": 92.0, "wobbe_index": 50.5, "gcv_mmbtu": 1088, "contract": "Long-term",  "route_risk": 0.10, "freight_day_rate": 88000,  "voyage_days": 14},
    {"name": "Freeport LNG",          "country": "USA",       "methane_pct": 95.5, "wobbe_index": 53.0, "gcv_mmbtu": 1110, "contract": "Spot",       "route_risk": 0.12, "freight_day_rate": 110000, "voyage_days": 28},
    {"name": "Corpus Christi LNG",    "country": "USA",       "methane_pct": 95.0, "wobbe_index": 52.8, "gcv_mmbtu": 1108, "contract": "Spot",       "route_risk": 0.12, "freight_day_rate": 108000, "voyage_days": 28},
    {"name": "Sakhalin-2 SEIC",       "country": "Russia",    "methane_pct": 89.5, "wobbe_index": 48.5, "gcv_mmbtu": 1062, "contract": "Long-term",  "route_risk": 0.60, "freight_day_rate": 80000,  "voyage_days": 8},
    {"name": "Bontang PLN",           "country": "Indonesia", "methane_pct": 88.0, "wobbe_index": 47.0, "gcv_mmbtu": 1045, "contract": "Spot",       "route_risk": 0.15, "freight_day_rate": 75000,  "voyage_days": 6},
]

# ─── Price Data (Static / Mock — upgrade to live feed later) ─────────────────
PRICE_DATA = {
    "JKM_USD_MMBtu":   14.25,
    "TTF_USD_MMBtu":   11.80,
    "HenryHub_USD_MMBtu": 2.85,
    "Brent_USD_bbl":   80.50,
    "Dubai_USD_bbl":   79.20,
    "WTI_USD_bbl":     77.80
}

def match_lng_suppliers(
    deficit_mmscmd: float,
    terminal_name: str,
    disrupted_countries: list = None
) -> Dict[str, Any]:
    """
    Match available LNG suppliers for a terminal, compute Replacement Viability Score.
    Lower score = better match. Avoids disrupted_countries if specified.
    """
    terminal = LNG_TERMINALS.get(terminal_name, LNG_TERMINALS["Dahej"])
    
    df = pd.DataFrame(LNG_SUPPLIERS)
    
    # Filter out disrupted countries
    if disrupted_countries:
        df = df[~df["country"].isin(disrupted_countries)].copy()
    
    # Terminal-specific Wobbe Index tolerance (each FSRU/terminal has a spec)
    target_wobbe = 50.0  # typical spec
    target_methane = 91.0
    target_gcv = 1080

    df["Delta_Wobbe"]   = np.abs(df["wobbe_index"]  - target_wobbe)
    df["Delta_Methane"] = np.abs(df["methane_pct"]  - target_methane)
    df["Freight_Cost"]  = (df["freight_day_rate"] * df["voyage_days"]) / 1e6  # $M per cargo

    # Viability Score
    df["Viability_Score"] = (
        1.5  * df["Delta_Methane"] +
        2.0  * df["Delta_Wobbe"]   +
        0.5  * df["Freight_Cost"]  +
        5.0  * df["route_risk"]
    )

    df = df.sort_values("Viability_Score").reset_index(drop=True)
    top = df[["name", "country", "contract", "methane_pct", "wobbe_index", "Freight_Cost", "route_risk", "Viability_Score"]].head(3)

    return {
        "terminal": terminal_name,
        "terminal_capacity_mmscmd": terminal["send_out_mmscmd"],
        "requested_mmscmd": deficit_mmscmd,
        "utilization_pct": terminal["utilization_pct"],
        "available_headroom_mmscmd": round(terminal["send_out_mmscmd"] * (1 - terminal["utilization_pct"]/100), 2),
        "top_suppliers": top.to_dict("records"),
        "prices": PRICE_DATA
    }

def calculate_regasification_plan(total_deficit_mmscmd: float) -> Dict[str, Any]:
    """
    Distribute the total gas deficit across all LNG terminals by available headroom.
    Priority: highest unused capacity first.
    """
    plan = []
    remaining = total_deficit_mmscmd

    sorted_terminals = sorted(
        LNG_TERMINALS.items(),
        key=lambda x: x[1]["send_out_mmscmd"] * (1 - x[1]["utilization_pct"]/100),
        reverse=True
    )

    for name, t in sorted_terminals:
        if remaining <= 0:
            break
        headroom = round(t["send_out_mmscmd"] * (1 - t["utilization_pct"]/100), 2)
        allocated = min(headroom, remaining)
        if allocated > 0:
            plan.append({
                "terminal": name,
                "operator": t["operator"],
                "allocated_mmscmd": round(allocated, 2),
                "new_utilization_pct": round(t["utilization_pct"] + (allocated/t["send_out_mmscmd"])*100, 1),
                "pipeline": t["pipeline"]
            })
            remaining = round(remaining - allocated, 2)

    return {
        "total_deficit_mmscmd": total_deficit_mmscmd,
        "deficit_covered_mmscmd": round(total_deficit_mmscmd - max(remaining, 0), 2),
        "shortfall_mmscmd": round(max(remaining, 0), 2),
        "terminal_plan": plan
    }


if __name__ == "__main__":
    print("Testing LNG Supplier Match for Dahej terminal, 3 MMSCMD deficit...")
    result = match_lng_suppliers(3.0, "Dahej", disrupted_countries=["Qatar"])
    print(result)
    print("\nTesting Regasification Plan for 8 MMSCMD total deficit...")
    plan = calculate_regasification_plan(8.0)
    for t in plan["terminal_plan"]:
        print(t)
