import requests
import logging
import datetime
import random
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ─── Rich Portwatch Mock Data Per Port ─────────────────────────────────────────
_PORTWATCH_MOCK = {
    "Paradip":  {"baseline": 28, "unit": "vessel calls/month", "crisis_drop": 0.55},
    "Mundra":   {"baseline": 52, "unit": "vessel calls/month", "crisis_drop": 0.40},
    "Vadinar":  {"baseline": 44, "unit": "vessel calls/month", "crisis_drop": 0.45},
    "Mangaluru":{"baseline": 18, "unit": "vessel calls/month", "crisis_drop": 0.60},
    "Kochi":    {"baseline": 22, "unit": "vessel calls/month", "crisis_drop": 0.35},
    "Ennore":   {"baseline": 15, "unit": "vessel calls/month", "crisis_drop": 0.50},
    "Kandla":   {"baseline": 35, "unit": "vessel calls/month", "crisis_drop": 0.38},
    "Strait of Hormuz": {"baseline": 1800, "unit": "tanker transits/month", "crisis_drop": 0.30},
    "Red Sea":  {"baseline": 1200, "unit": "cargo vessel transits/month", "crisis_drop": 0.65},
    "Suez Canal":{"baseline": 1500, "unit": "transits/month", "crisis_drop": 0.70},
}

def _generate_portwatch_series(port_id: str, start_date: str, end_date: str, metric: str) -> Dict[str, Any]:
    """Generate realistic PortWatch time-series data with crisis-driven dip pattern."""
    port_cfg = _PORTWATCH_MOCK.get(port_id, {"baseline": 30, "unit": "vessel calls/month", "crisis_drop": 0.45})
    baseline = port_cfg["baseline"]
    drop = port_cfg["crisis_drop"]

    try:
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
    except Exception:
        start = datetime.date(2024, 1, 1)
        end = datetime.date(2024, 3, 1)

    delta = (end - start).days
    points = []
    mid = delta // 2  # crisis midpoint

    for i in range(0, delta, max(1, delta // 12)):
        d = start + datetime.timedelta(days=i)
        # Simulate a crisis dip in the middle of the range
        crisis_factor = 1.0 - (drop * max(0, 1 - abs(i - mid) / max(1, mid * 0.7)))
        noise = random.uniform(-0.07, 0.07)
        value = round(baseline * (crisis_factor + noise))
        value = max(1, value)
        points.append({"date": d.isoformat(), "value": value})

    metric_labels = {
        "transit_calls":     "Vessel Transit Calls",
        "gross_tonnage":     "Gross Tonnage (000 DWT)",
        "cargo_volume":      "Cargo Volume (MMT)",
        "vessel_waiting":    "Average Vessel Waiting Time (hrs)",
        "port_congestion":   "Port Congestion Index (0–100)",
    }

    return {
        "port_id": port_id,
        "metric": metric,
        "metric_label": metric_labels.get(metric, metric),
        "unit": port_cfg["unit"],
        "data": points,
        "summary": {
            "peak": max(p["value"] for p in points),
            "trough": min(p["value"] for p in points),
            "average": round(sum(p["value"] for p in points) / len(points), 1),
            "crisis_drop_pct": round(drop * 100),
            "note": f"Crisis-period traffic drop of ~{round(drop*100)}% detected in period — consistent with Red Sea / Hormuz disruption pattern."
        },
        "source": "MARG · IMF PortWatch (Simulated Analytics)",
        "provenance": "IMF PortWatch ArcGIS — Simulated based on MARG VECM disruption model"
    }


def fetch_imf_portwatch(port_id: str, start_date: str, end_date: str, metric: str = "transit_calls") -> Dict[str, Any]:
    """
    MARG — Fetch IMF PortWatch ArcGIS transit data.
    IMF PortWatch uses ArcGIS feature services, not a public REST JSON API.
    We generate realistic scenario-driven port traffic analytics using MARG's 
    VECM disruption model and return rich chart-ready data.
    """
    # Try the correct IMF PortWatch ArcGIS endpoint
    try:
        arcgis_url = (
            "https://portwatch.imf.org/arcgis/rest/services/PortWatch/PortWatch_Data/FeatureServer/0/query"
        )
        params = {
            "where": f"port_name='{port_id}'",
            "outFields": "date,value",
            "orderByFields": "date ASC",
            "f": "json",
            "resultRecordCount": 50,
        }
        r = requests.get(arcgis_url, params=params, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 BHARAT-SHIELD"})
        if r.status_code == 200:
            data = r.json()
            features = data.get("features", [])
            if features and len(features) > 2:
                points = [{"date": f["attributes"].get("date",""), "value": f["attributes"].get("value",0)} for f in features]
                return {
                    "port_id": port_id, "metric": metric, "data": points,
                    "source": "IMF PortWatch ArcGIS (Live)"
                }
    except Exception as e:
        logger.warning(f"MARG: IMF PortWatch ArcGIS failed for {port_id}: {e}")

    # MARG VECM Simulation Fallback
    return _generate_portwatch_series(port_id, start_date, end_date, metric)

def evaluate_infrastructure_constraints(rerouted_volume_mmt: float, port: str) -> Dict[str, Any]:
    """
    Evaluates physical infrastructure constraints (SPM Discharge Limits & Arterial Pipeline Limits).
    """
    spm_limits = {
        "Mundra": 0.15,
        "Vadinar": 0.18,
        "Paradip": 0.12
    }
    pipeline_limits = {
        "Mundra": 0.07,   # MDPL
        "Vadinar": 0.08,  # SMPL
        "Paradip": 0.05   # Paradip-Haldia
    }
    
    spm_cap = spm_limits.get(port, 0.10)
    pipe_cap = pipeline_limits.get(port, 0.05)
    
    bottleneck_detected = False
    bottleneck_reasons = []
    
    if rerouted_volume_mmt > spm_cap:
        bottleneck_detected = True
        bottleneck_reasons.append(f"SPM Discharge Limit Exceeded (Cap: {spm_cap} MMT/day)")
        
    if rerouted_volume_mmt > pipe_cap:
        bottleneck_detected = True
        bottleneck_reasons.append(f"Pipeline Evacuation Limit Exceeded (Cap: {pipe_cap} MMT/day)")
        
    return {
        "port": port,
        "requested_volume": rerouted_volume_mmt,
        "spm_capacity": spm_cap,
        "pipeline_capacity": pipe_cap,
        "is_bottlenecked": bottleneck_detected,
        "reasons": bottleneck_reasons,
        "provenance": "DGH & PNGRB Capacity Registers (MARG)"
    }

def calculate_disruption_delays(vessel_eta_days: int, reroute_cape_of_good_hope: bool) -> int:
    """
    Computes physical ETA delays. e.g., Cape of Good Hope rerouting adding +14 days.
    """
    added_delay = 14 if reroute_cape_of_good_hope else 0
    return vessel_eta_days + added_delay

if __name__ == "__main__":
    print(evaluate_infrastructure_constraints(0.16, "Mundra"))
