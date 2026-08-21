import logging
import math
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ─── Refinery Metallurgy Constraints Database ─────────────────────────────────
REFINERY_LIMITS = {
    "Paradip": {
        "max_sulfur": 3.5, "max_tan": 1.2, "min_api": 20, "max_api": 48,
        "desulfurization_capacity_pct": 90,
        "operator": "IOCL", "capacity_mmtpa": 15.0,
        "note": "High TAN tolerance, moderate sulfur tolerance"
    },
    "Jamnagar": {
        "max_sulfur": 5.0, "max_tan": 0.5, "min_api": 18, "max_api": 50,
        "desulfurization_capacity_pct": 95,
        "operator": "RIL", "capacity_mmtpa": 62.0,
        "note": "World's largest refinery complex — extremely high sulfur tolerance"
    },
    "MRPL": {
        "max_sulfur": 1.5, "max_tan": 0.2, "min_api": 28, "max_api": 46,
        "desulfurization_capacity_pct": 70,
        "operator": "MRPL", "capacity_mmtpa": 15.0,
        "note": "Strict metallurgy — low sulfur and very low acid tolerance"
    },
    "Kochi": {
        "max_sulfur": 1.8, "max_tan": 0.3, "min_api": 25, "max_api": 47,
        "desulfurization_capacity_pct": 75,
        "operator": "BPCL", "capacity_mmtpa": 15.5,
        "note": "Sweet crude focused — moderate constraints"
    },
    "Bina": {
        "max_sulfur": 2.5, "max_tan": 0.6, "min_api": 22, "max_api": 46,
        "desulfurization_capacity_pct": 80,
        "operator": "BPCL-Oman", "capacity_mmtpa": 7.8,
        "note": "Designed for Omani crude — moderate overall tolerance"
    },
}

# ─── Historical Crisis Analog Database ────────────────────────────────────────
CRISIS_ANALOGS = [
    {
        "event": "2021 Ever Given Suez Canal Blockage",
        "region_keywords": ["suez", "suez canal", "ever given"],
        "similarity_score": 88,
        "duration_days": 6,
        "brent_spike_usd": 4.0,
        "transit_delay_days": 12,
        "outcome": "Brent spiked $4/bbl for 6 days. 400+ ships queued. Cape rerouting added 12–14 days. Indian refineries drawn on commercial stocks."
    },
    {
        "event": "2019 Abqaiq / Khurais Drone Attack",
        "region_keywords": ["saudi", "abqaiq", "aramco", "khurais"],
        "similarity_score": 82,
        "duration_days": 3,
        "brent_spike_usd": 14.6,
        "transit_delay_days": 0,
        "outcome": "Largest single oil supply disruption ever. Brent spiked $14.6/bbl in 1 day. Saudi cut 5.7 MMT/month. India activated ISPRL within 48 hours. Recovered in 3 weeks."
    },
    {
        "event": "2024 Houthi Red Sea Campaign",
        "region_keywords": ["red sea", "houthi", "bab-el-mandeb", "bab el mandeb"],
        "similarity_score": 95,
        "duration_days": 90,
        "brent_spike_usd": 5.0,
        "transit_delay_days": 14,
        "outcome": "Sustained 3-month disruption. 90% of transiting tankers rerouted via Cape. Freight costs surged 300%. India's Middle East crude costs rose ~$2.50/bbl."
    },
    {
        "event": "2022 Russia–Ukraine Sanctions Shock",
        "region_keywords": ["russia", "urals", "sanction", "ukraine"],
        "similarity_score": 75,
        "duration_days": 365,
        "brent_spike_usd": 28.0,
        "transit_delay_days": 3,
        "outcome": "Brent hit $130/bbl. Europe banned Russian Urals. India opportunistically absorbed discounted Urals at $30/bbl below Brent. Russian share of India crude basket rose from 2% to 40%."
    },
    {
        "event": "2022 Freeport LNG Outage",
        "region_keywords": ["freeport", "lng", "usa", "usg"],
        "similarity_score": 70,
        "duration_days": 180,
        "brent_spike_usd": 0,
        "transit_delay_days": 0,
        "outcome": "US LNG export capacity fell 15% for 6 months. JKM spiked $6/MMBtu. Asian buyers competed for Australian and Qatari cargoes. India renegotiated Dahej term contracts."
    },
    {
        "event": "2012 Hormuz Strait Closure Threat (Iran)",
        "region_keywords": ["hormuz", "iran", "strait", "gulf"],
        "similarity_score": 80,
        "duration_days": 45,
        "brent_spike_usd": 8.0,
        "transit_delay_days": 7,
        "outcome": "Iran threatened to mine Hormuz. 17 MMBbl/day at risk. Brent rose $8/bbl. India fast-tracked payment clearing for Iranian crude via rupee settlement. US 5th Fleet deployed."
    },
]

# ─── Refinery Run-Rate Impact Calculator ──────────────────────────────────────
def calculate_run_rate_impact(deficit_mmt: float, refinery: str) -> Dict[str, Any]:
    """
    Calculates how many days before refinery run-rate cuts begin,
    what percentage cut to expect, and downstream product impacts.
    """
    specs = REFINERY_LIMITS.get(refinery, REFINERY_LIMITS["Paradip"])
    capacity_mmtpa = specs["capacity_mmtpa"]
    daily_capacity_mmt = round(capacity_mmtpa / 330, 4)  # 330 operating days/year
    
    # Assume 15-day forward stock buffer at normal operations
    buffer_days = 15
    buffer_mmt = round(daily_capacity_mmt * buffer_days, 3)
    
    net_shortfall_after_buffer = max(0, deficit_mmt - buffer_mmt)
    run_rate_cut_pct = round(min(100, (net_shortfall_after_buffer / daily_capacity_mmt) * 100 / 30), 1)
    
    days_before_rationing = buffer_days if deficit_mmt > buffer_mmt else None
    
    # Downstream product impact
    products_at_risk = []
    if run_rate_cut_pct > 0:
        products_at_risk.append(f"Petrol/HSD (auto fuel): {round(run_rate_cut_pct * 0.35, 1)}% output reduction")
        products_at_risk.append(f"Naphtha (petrochemicals): {round(run_rate_cut_pct * 0.18, 1)}% output reduction")
        if run_rate_cut_pct > 20:
            products_at_risk.append("Aviation turbine fuel (ATF): shortfall risk within 7 days")

    return {
        "refinery": refinery,
        "operator": specs["operator"],
        "daily_capacity_mmt": daily_capacity_mmt,
        "forward_buffer_mmt": buffer_mmt,
        "buffer_days": buffer_days,
        "net_shortfall_mmt": round(net_shortfall_after_buffer, 3),
        "run_rate_cut_pct": run_rate_cut_pct,
        "days_before_rationing": days_before_rationing,
        "products_at_risk": products_at_risk,
        "provenance": f"PPAC & MoP&NG Refinery Capacity Register ({refinery})"
    }

# ─── 7-Day Recovery Timeline ──────────────────────────────────────────────────
def generate_recovery_timeline(deficit_mmt: float, port: str, distance_nm: float, commodity: str = "crude") -> List[Dict]:
    """
    Generates a day-by-day strategic recovery timeline from crisis onset.
    """
    transit_days = max(8, int(distance_nm / (12 * 24)))  # 12 knots avg
    
    if commodity == "crude":
        timeline = [
            {"day": 1,  "phase": "ALERT",    "action": "BHARAT-SHIELD threat detection. Cabinet Committee on Economic Affairs (CCEA) notified. Director-General of Hydrocarbons on standby."},
            {"day": 2,  "phase": "MOBILIZE", "action": f"MoP&NG issues Phase I drawdown order. IOCL, BPCL, HPCL commercial reserves release begins. ISPRL Visakhapatnam cavern valve opened."},
            {"day": 3,  "phase": "PROCURE",  "action": f"IOC and BPCL trading desks contact spot market. Brokers in Ras Tanura, Dubai, Singapore activated for {deficit_mmt} MMT emergency tender."},
            {"day": 5,  "phase": "TRANSIT",  "action": f"First emergency cargo departs {port.upper() if commodity=='crude' else 'Ras Laffan'}. ETA to Indian coast: {transit_days} days. War Risk insurance arranged via Lloyd's."},
            {"day": 7,  "phase": "MONITOR",  "action": "Refinery intake adjusted. Secondary supply lines from Russian ESPO (Paradip) and US WTI (Mundra) confirmed as backup. Daily situation briefing to PMO."},
            {"day": transit_days + 5, "phase": "RECEIPT", "action": f"Emergency cargo begins berthing at {port}. SPM discharge commences. Daily offload: {0.12} MMT/day. Pipeline evacuation to tankfarm active."},
            {"day": transit_days + 10, "phase": "NORMALIZE", "action": "Strategic reserve drawdown pauses. Spot cargoes bridge remaining gap. Normal refinery run-rate resumed. ISPRL replenishment tender issued."},
        ]
    else:
        timeline = [
            {"day": 1,  "phase": "ALERT",    "action": "Gas supply disruption detected. PNGRB and MoPNG notified. Gas grid operator (GAIL) places all LNG terminals on standby."},
            {"day": 2,  "phase": "MOBILIZE", "action": "Dahej and Hazira LNG terminals instructed to maximize send-out from heel inventory. City gas companies placed on priority allocation."},
            {"day": 3,  "phase": "PROCURE",  "action": "India LNG tender issued on Singapore exchange. QatarEnergy, Shell LNG, TotalEnergies contacted for spot cargoes."},
            {"day": 6,  "phase": "TRANSIT",  "action": f"First emergency LNG cargo departs Ras Laffan. Q-Flex carrier ({210000}m³ / ~{round(210000*0.00046, 1)} MMSCMD). ETA: {transit_days} days."},
            {"day": 8,  "phase": "MONITOR",  "action": "Domestic field operators (ONGC KG Basin, Reliance D6) instructed to ramp up well deliverability. HVJ pipeline pressure increased."},
            {"day": transit_days + 4, "phase": "RECEIPT", "action": "Emergency LNG cargo arrives. Regasification commences at full nameplate capacity. Spot cargo injected into national gas grid."},
            {"day": transit_days + 8, "phase": "NORMALIZE", "action": "Gas grid pressure normalized. Second spot cargo dispatched from Freeport LNG. Fertilizer plants restored to 100% capacity."},
        ]
    
    return timeline

# ─── Supply Chain Risk Index ──────────────────────────────────────────────────
def compute_supply_risk_index(
    corridor_risk: float,
    is_bottlenecked: bool,
    critic_warning_count: int,
    deficit_mmt: float
) -> Dict[str, Any]:
    """
    Computes a composite 0–100 Supply Chain Risk Index (SCRI).
    Combines geopolitical risk, infrastructure bottleneck, critic alerts, and deficit severity.
    """
    geopolitical_score = corridor_risk * 40   # max 40 pts
    bottleneck_score   = 20 if is_bottlenecked else 0   # 20 pts
    critic_score       = min(25, critic_warning_count * 10)  # max 25 pts
    deficit_score      = min(15, deficit_mmt * 1.5)          # max 15 pts

    total = round(geopolitical_score + bottleneck_score + critic_score + deficit_score, 1)
    
    band = "LOW" if total < 30 else "MODERATE" if total < 55 else "HIGH" if total < 75 else "CRITICAL"
    color = {"LOW": "green", "MODERATE": "yellow", "HIGH": "orange", "CRITICAL": "red"}[band]
    
    return {
        "score": total,
        "band": band,
        "color": color,
        "breakdown": {
            "geopolitical": round(geopolitical_score, 1),
            "infrastructure_bottleneck": bottleneck_score,
            "critic_warnings": critic_score,
            "deficit_severity": round(deficit_score, 1),
        }
    }

# ─── Historical Analog Matcher ────────────────────────────────────────────────
def find_historical_analog(region: str, commodity: str = "crude") -> Optional[Dict]:
    """
    Finds the best-matching historical crisis analog for contextual decision support.
    """
    region_lower = region.lower()
    best_match = None
    best_score = 0

    for analog in CRISIS_ANALOGS:
        for keyword in analog["region_keywords"]:
            if keyword in region_lower:
                # If this analog matches better than previous
                if analog["similarity_score"] > best_score:
                    best_score = analog["similarity_score"]
                    best_match = analog
                break

    return best_match

# ─── Comprehensive Vulnerability Assessment ────────────────────────────────────
def evaluate_plan_vulnerabilities(sim_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Red Team / Devil's Advocate Agent (Agent 6).
    Performs multi-layer vulnerability analysis: infrastructure, metallurgy,
    strategic reserve depletion, and LNG shortfall risks.
    """
    warnings = []
    commodity = sim_data.get("commodity", "crude")
    region = sim_data.get("region", "")

    if commodity in ("crude", "both") and "crude" in sim_data:
        c_data = sim_data["crude"]
        infra = c_data.get("agent2_infrastructure_check", {})
        drawdown = c_data.get("agent4_drawdown_plan", {})
        alts = c_data.get("agent3_crude_alternatives", [])
        refinery = c_data.get("scenario_parsed", {}).get("refinery", "Paradip")

        # 1. SPM / Pipeline bottleneck check
        if infra.get("is_bottlenecked"):
            warnings.append({
                "type": "INFRASTRUCTURE_CHOKE",
                "severity": "HIGH",
                "message": (
                    f"Port {infra.get('port', 'target')} is operating beyond SPM/pipeline capacity. "
                    f"The proposed emergency crude cannot be offloaded at the required rate. "
                    f"Expect demurrage costs of ~$35,000/day per waiting VLCC. "
                    f"Consider splitting cargo across Vadinar + Paradip or pre-booking additional berths."
                )
            })

        # 2. Southern ISPRL depletion check
        isprl = drawdown.get("ISPRL_Drawdown", {})
        southern_draw = isprl.get("Padur", 0) + isprl.get("Mangaluru", 0)
        if southern_draw > 0.5:
            warnings.append({
                "type": "STRATEGIC_RESERVE_DEPLETION_SOUTH",
                "severity": "CRITICAL" if southern_draw > 1.0 else "MEDIUM",
                "message": (
                    f"Drawing {round(southern_draw, 2)} MMT from Southern ISPRL caverns (Padur + Mangaluru) "
                    f"solves the immediate {round(c_data.get('scenario_parsed', {}).get('deficit_mmt', 0), 1)} MMT deficit "
                    f"but leaves South India's strategic buffer exposed. "
                    f"If disruption extends beyond 30 days, Chennai/Kochi refineries face secondary shortfalls. "
                    f"Recommend authorizing Visakhapatnam draws first to preserve southern cover."
                )
            })

        # 3. Metallurgy mismatch check using actual assay data
        ref_limits = REFINERY_LIMITS.get(refinery, {})
        if alts and ref_limits:
            best = alts[0]
            crude_name = best.get("Crude_Name", "")
            # Look up in common flagged crudes
            high_sulfur_crudes = ["Basrah Heavy", "Iran Heavy", "Arab Heavy", "Mars Blend", "Merey (Venezuela)", "Russian Urals"]
            high_tan_crudes = ["Merey (Venezuela)", "Basrah Heavy", "Guyana Liza"]
            
            issues = []
            if crude_name in high_sulfur_crudes and ref_limits.get("max_sulfur", 5) < 2.0:
                issues.append(f"high sulfur content (>2%) exceeds {refinery} desulfurization capacity of {ref_limits['desulfurization_capacity_pct']}%")
            if crude_name in high_tan_crudes and ref_limits.get("max_tan", 1) < 0.5:
                issues.append(f"high TAN acid content risks corrosion damage to {refinery} atmospheric distillation units")
            
            if issues:
                warnings.append({
                    "type": "METALLURGY_MISMATCH",
                    "severity": "HIGH",
                    "message": (
                        f"Top replacement crude {crude_name} flagged: {'; '.join(issues)}. "
                        f"This will trigger mandatory catalyst replacement cycles, "
                        f"estimated maintenance cost: $2–8M. "
                        f"Consider rank-2 alternative from the assay database."
                    )
                })

        # 4. Single-source supply risk
        if alts and len(alts) < 2:
            warnings.append({
                "type": "SUPPLY_CONCENTRATION_RISK",
                "severity": "MEDIUM",
                "message": (
                    "Only 1 viable replacement crude identified. "
                    "Concentrating emergency procurement on a single grade increases "
                    "price leverage by sellers. Recommend parallel tender for 2+ grades."
                )
            })

    if commodity in ("gas", "both") and "gas" in sim_data:
        g_data = sim_data["gas"]
        plan = g_data.get("agent4_regasification_plan", {})
        shortfall = plan.get("shortfall_mmscmd", 0)
        
        if shortfall > 0:
            warnings.append({
                "type": "GAS_REGASIFICATION_SHORTFALL",
                "severity": "CRITICAL",
                "message": (
                    f"Even at maximum terminal utilization, {round(shortfall, 1)} MMSCMD cannot be covered "
                    f"through LNG regasification alone. Mandatory curtailment of non-essential industrial consumers "
                    f"(fertilizer plants, glass/ceramics) will be required. "
                    f"PNGRB must issue Emergency Gas Allocation Order within 24 hours."
                )
            })

        # 5. Qatar concentration risk for gas
        dis_ctries = g_data.get("scenario_parsed", {}).get("disrupted_countries", [])
        top_suppliers = g_data.get("agent3_lng_suppliers", {}).get("top_suppliers", [])
        if "Qatar" in dis_ctries and any(s.get("country") == "Qatar" for s in top_suppliers[:2]):
            warnings.append({
                "type": "LNG_SUPPLIER_CONCENTRATION",
                "severity": "HIGH",
                "message": (
                    "Qatar is both the disrupted country AND the primary recommended supplier. "
                    "This creates a circular dependency. Recommend diversifying to Australian Woodside "
                    "or US Freeport LNG cargoes, accepting a $1.50–2.00/MMBtu cost premium."
                )
            })

    # Find historical analog
    historical_analog = find_historical_analog(region, commodity)

    return {
        "assessment_status": "COMPLETED",
        "warnings": warnings,
        "historical_analog": historical_analog
    }
