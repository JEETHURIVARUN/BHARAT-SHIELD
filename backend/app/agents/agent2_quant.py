import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def fetch_imf_portwatch(port_id: str, start_date: str, end_date: str, metric: str = "transit_calls") -> Dict[str, Any]:
    """
    Fetch IMF PortWatch transit data with changeable parameters.
    The parameters will change based on our requirements (e.g., metric, port_id, date range).
    """
    base_url = f"https://portwatch.imf.org/api/v1/ports/{port_id}/data"
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "metric": metric
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching IMF PortWatch data for {port_id}: {e}")
        return {
            "port_id": port_id,
            "metric": metric,
            "data": [
                {"date": start_date, "value": 15},
                {"date": end_date, "value": 12}
            ],
            "note": "Mocked fallback data"
        }

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
