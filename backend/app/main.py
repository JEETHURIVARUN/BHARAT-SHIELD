from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime, hashlib, json, logging, os, re, asyncio
import websockets
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.agents.agent1_sentinel import fetch_ukmto_incidents, fetch_gdelt_data
from app.agents.agent1_event_graph import build_incident_graph          # Upgrade 1
from app.agents.agent2_quant import fetch_imf_portwatch, evaluate_infrastructure_constraints, calculate_disruption_delays
from app.agents.agent2_dead_reckoning import enrich_vessels_with_dead_reckoning  # Upgrade 2
from app.agents.agent3_trader import calculate_maritime_route, match_crude_assays
from app.agents.agent3_gas_trader import match_lng_suppliers, calculate_regasification_plan, LNG_TERMINALS, PRICE_DATA
from app.agents.agent4_governor import solve_drawdown, Phase
from app.agents.agent4_gas_governor import solve_gas_drawdown
from app.agents.agent5_war_room import generate_audit_package
from app.agents.agent6_critic import evaluate_plan_vulnerabilities
from app.agents.shared_models import _load_assays, estimate_price_shock, calculate_rerouting_delay, compute_risk_score
from app.db.session_store import (                                       # Upgrade 5
    init_db, save_snapshot, list_snapshots, get_snapshot_by_id,
    get_latest_snapshot, get_age_of_latest_seconds
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BHARAT-SHIELD API v2")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ─── Persistent Strategic Fleet & Live AIS Store ──────────────────────────────
_INIT_TIME = datetime.datetime.now(datetime.timezone.utc)
_CORE_STRATEGIC_FLEET = {
    # Indian Sovereign Tankers (Shipping Corporation of India & Great Eastern)
    "419088600": {"mmsi": "419088600", "name": "DESH VIBHOR",       "type": "VLCC Tanker",    "lon": 62.5, "lat": 20.1, "speed": 12.4, "heading": 95,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419089200": {"mmsi": "419089200", "name": "DESH VIRAAT",       "type": "VLCC Tanker",    "lon": 82.1, "lat": 14.6, "speed": 11.2, "heading": 45,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419089500": {"mmsi": "419089500", "name": "DESH SHANTI",       "type": "VLCC Tanker",    "lon": 60.1, "lat": 22.8, "speed": 12.8, "heading": 110, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419000851": {"mmsi": "419000851", "name": "SWARNA SINDHU",     "type": "Suezmax Tanker", "lon": 67.4, "lat": 18.5, "speed": 13.0, "heading": 75,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419000862": {"mmsi": "419000862", "name": "SWARNA JAYANTI",    "type": "Aframax Tanker", "lon": 72.8, "lat": 16.2, "speed": 12.5, "heading": 350, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419075300": {"mmsi": "419075300", "name": "JAG LEELA",         "type": "Crude Tanker",   "lon": 65.8, "lat": 21.0, "speed": 11.5, "heading": 85,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "419076100": {"mmsi": "419076100", "name": "JAG LOK",           "type": "Crude Tanker",   "lon": 75.0, "lat": 11.8, "speed": 12.0, "heading": 15,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    # Strategic LNG & Dedicated Energy Supply Carriers
    "310565000": {"mmsi": "310565000", "name": "LNG IMO",           "type": "LNG Carrier",    "lon": 44.2, "lat": 12.8, "speed": 16.5, "heading": 115, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "408848000": {"mmsi": "408848000", "name": "MILAHA RAS LAFFAN", "type": "LNG Carrier",    "lon": 58.4, "lat": 21.2, "speed": 17.2, "heading": 92,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "311756000": {"mmsi": "311756000", "name": "AL DAAYEN",         "type": "LNG Carrier",    "lon": 52.1, "lat": 25.4, "speed": 18.0, "heading": 130, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "466007000": {"mmsi": "466007000", "name": "AL GHARIYA",        "type": "LNG Carrier",    "lon": 64.0, "lat": 22.0, "speed": 17.5, "heading": 100, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    # International Energy Charters bound for India
    "538006325": {"mmsi": "538006325", "name": "FRONT ALTAIR",      "type": "VLCC Tanker",    "lon": 55.8, "lat": 23.5, "speed": 13.1, "heading": 105, "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "563032700": {"mmsi": "563032700", "name": "ASIAN PROGRESS VI", "type": "VLCC Tanker",    "lon": 68.2, "lat": 19.8, "speed": 11.8, "heading": 88,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "352163000": {"mmsi": "352163000", "name": "ATLANTIC PIONEER",  "type": "VLCC Tanker",    "lon": 74.3, "lat": 18.2, "speed": 10.5, "heading": 70,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
    "240899000": {"mmsi": "240899000", "name": "MARAN APHRODITE",   "type": "Suezmax Tanker", "lon": 63.8, "lat": 23.1, "speed": 12.9, "heading": 98,  "status": "Underway", "last_update_utc": _INIT_TIME.isoformat()},
}

_LIVE_VESSELS = dict(_CORE_STRATEGIC_FLEET)

from app.agents.agent2_dead_reckoning import (
    enrich_vessels_with_dead_reckoning,
    get_vessel_geopolitics,
    is_in_strategic_theater
)

async def _aisstream_listener():
    api_key = os.getenv("AISSTREAM_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        logger.warning("AISSTREAM_API_KEY not found or invalid. Using persistent strategic fleet baseline.")
        return

    # Strategic maritime bounding box: Indian Ocean, Arabian Sea, Bay of Bengal, Persian Gulf, Red Sea, Malacca
    # [[ [lat_min, lon_min], [lat_max, lon_max] ]]
    subscribe_message = {
        "APIKey": api_key,
        "BoundingBoxes": [[[-15.0, 35.0], [32.0, 105.0]]],
        "FilterMessageTypes": ["PositionReport"]
    }

    while True:
        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                await ws.send(json.dumps(subscribe_message))
                logger.info("Connected to AISStream WebSocket — Strategic Theater Filtering Active")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("MessageType") == "PositionReport":
                        meta = data.get("MetaData", {})
                        pr = data.get("Message", {}).get("PositionReport", {})
                        
                        mmsi = str(meta.get("MMSI", "")).strip()
                        if not mmsi or len(mmsi) < 3:
                            continue

                        lon = pr.get("Longitude", 0)
                        lat = pr.get("Latitude", 0)

                        # Filter 1: Must fall inside India's Strategic Maritime Energy Corridor
                        if not is_in_strategic_theater(lon, lat):
                            continue

                        # Filter 2: Must be India, strategic energy partner, neighbouring maritime, or energy charter
                        geo = get_vessel_geopolitics(mmsi)
                        sog = pr.get("Sog", 0)
                        ship_name = meta.get("ShipName", "").strip() or f"Vessel {mmsi}"

                        # Determine vessel type
                        is_lng = any(k in ship_name.upper() for k in ["LNG", "GAS", "METHANE", "Q-FLEX", "Q-MAX"])
                        vtype = "LNG Carrier" if is_lng else "Tanker"

                        _LIVE_VESSELS[mmsi] = {
                            "mmsi": mmsi,
                            "name": ship_name,
                            "type": vtype,
                            "lon":  lon,
                            "lat":  lat,
                            "speed":   sog,
                            "heading": pr.get("TrueHeading", 0),
                            "status":  "Underway" if sog > 0.5 else "Anchored",
                            "last_update_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                        
                        # Maintain generous capacity with 24h expiration
                        if len(_LIVE_VESSELS) > 1500:
                            now = datetime.datetime.now(datetime.timezone.utc)
                            # Only purge non-core vessels older than 24h
                            stale_keys = [
                                k for k, v in _LIVE_VESSELS.items()
                                if k not in _CORE_STRATEGIC_FLEET and (now - datetime.datetime.fromisoformat(v.get("last_update_utc", now.isoformat()))).total_seconds() > 86400
                            ]
                            for k in stale_keys[:100]:
                                _LIVE_VESSELS.pop(k, None)
        except Exception as e:
            logger.error(f"AISStream WebSocket error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    init_db()                                    # Upgrade 5: init SQLite session store
    asyncio.create_task(_aisstream_listener())


PORT_COORDINATES = {
    "Mundra":   [69.7, 22.8], "Vadinar":  [69.7, 22.4],
    "Paradip":  [86.6, 20.2], "Jamnagar": [70.0, 22.4],
    "Mangaluru":[74.8, 12.9], "Dahej":    [72.5, 21.7],
    "Hazira":   [72.6, 21.1], "Kochi":    [76.2, 10.0],
    "Ennore":   [80.3, 13.2],
}

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class DeficitRequest(BaseModel):
    daily_deficit_mmt: float
    phase: int = 1

class DirectiveRequest(BaseModel):
    authorization_token: str
    deficit_mmt: float
    phase: int = 1
    drawdown_plan: dict

class ScenarioRequest(BaseModel):
    daily_deficit_mmt: float
    target_refinery: str = "Paradip"
    port_of_discharge: str = "Paradip"

class IntelRequest(BaseModel):
    query: str
    incident_types: list = None

class PortWatchRequest(BaseModel):
    port_id: str
    start_date: str
    end_date: str
    metric: str = "transit_calls"

class RouteRequest(BaseModel):
    origin: list
    dest: list

# ─── LLM Parsing Helper ───────────────────────────────────────────────────────
def _parse_with_llm(message: str) -> dict:
    """Try OpenAI first, then Gemini as backup. Robust JSON extraction."""
    prompt = (
        "You are an energy crisis analyst for India's Ministry of Petroleum. "
        "Extract structured data from the user's crisis message.\n"
        "Return ONLY a valid JSON object with these exact keys:\n"
        "- commodity: 'crude' or 'gas' or 'both'\n"
        "- crude_deficit_mmt: float (crude oil deficit in MMT, 0 if not mentioned)\n"
        "- gas_deficit_mmscmd: float (gas deficit in MMSCMD, 0 if not mentioned)\n"
        "- refinery: string (Indian refinery: Paradip, Jamnagar, MRPL, Kochi, Bina — default 'Paradip')\n"
        "- port: string (Indian port: Paradip, Mundra, Vadinar, Mangaluru — default 'Paradip')\n"
        "- lng_terminal: string (LNG terminal: Dahej, Hazira, Kochi, Ennore — default 'Dahej')\n"
        "- disrupted_region: string (e.g. 'Red Sea', 'Hormuz', 'Suez Canal')\n"
        "- disrupted_countries: list of country strings\n"
        f"User message: {message}"
    )
    
    # Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key and not openai_key.startswith("your_"):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.output_parsers import JsonOutputParser
            from langchain_core.prompts import ChatPromptTemplate
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, timeout=15)
            chain = ChatPromptTemplate.from_template("{p}") | llm | JsonOutputParser()
            return chain.invoke({"p": prompt})
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}, trying Gemini...")

    # Try Gemini (new google-genai SDK)
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and not gemini_key.startswith("your_"):
        try:
            from google import genai as google_genai
            client = google_genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            text = response.text.strip()
            # Robust JSON extraction: strip markdown fences
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except ImportError:
            # Fallback to old google-generativeai SDK with updated model
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-2.0-flash-exp")
                resp = model.generate_content(prompt)
                text = resp.text.strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text.strip())
            except Exception as e2:
                logger.warning(f"Gemini (old SDK) failed: {e2}")
        except Exception as e:
            logger.warning(f"Gemini (new SDK) failed: {e}")

    return {}  # Both failed — use keyword fallback

def _keyword_parse(message: str) -> dict:
    """Fallback keyword extractor."""
    msg = message.lower()
    commodity = "both" if ("gas" in msg or "lng" in msg or "rlng" in msg) and ("crude" in msg or "oil" in msg) \
                else "gas" if ("gas" in msg or "lng" in msg) else "crude"

    crude_match = re.search(r'(\d+(?:\.\d+)?)\s*mmt', msg)
    gas_match   = re.search(r'(\d+(?:\.\d+)?)\s*mmscmd', msg)

    refinery = "Jamnagar" if "jamnagar" in msg or "ril" in msg else \
               "MRPL"     if "mrpl" in msg or "mangaluru" in msg else "Paradip"
    port = "Vadinar" if refinery == "Jamnagar" else \
           "Mangaluru" if refinery == "MRPL" else "Paradip"
    terminal = "Hazira" if "hazira" in msg else \
               "Kochi"  if "kochi" in msg  else "Dahej"
    disrupted = ["Qatar"] if "qatar" in msg else []
    region    = "Red Sea" if "red sea" in msg or "houthi" in msg else \
                "Hormuz"  if "hormuz" in msg else "General Disruption"

    return {
        "commodity": commodity,
        "crude_deficit_mmt":    float(crude_match.group(1)) if crude_match else (4.5 if commodity != "gas" else 0),
        "gas_deficit_mmscmd":   float(gas_match.group(1))   if gas_match   else (8.0 if commodity != "crude" else 0),
        "refinery": refinery, "port": port,
        "lng_terminal": terminal,
        "disrupted_region": region,
        "disrupted_countries": disrupted,
    }

# ─── Main Chat Simulation Endpoint ───────────────────────────────────────────
@app.post("/api/v1/chat-simulate")
async def chat_simulate(req: ChatRequest):
    from app.agents.agent6_critic import (
        evaluate_plan_vulnerabilities, calculate_run_rate_impact,
        generate_recovery_timeline, compute_supply_risk_index
    )

    # 1. Parse intent with LLM, fall back to keyword parser
    parsed = _parse_with_llm(req.message)
    if not parsed:
        parsed = _keyword_parse(req.message)
    logger.info(f"Parsed scenario: {parsed}")

    commodity  = parsed.get("commodity", "crude")
    c_deficit  = float(parsed.get("crude_deficit_mmt",  0) or 0)
    g_deficit  = float(parsed.get("gas_deficit_mmscmd", 0) or 0)
    refinery   = parsed.get("refinery",    "Paradip")
    port       = parsed.get("port",        "Paradip")
    terminal   = parsed.get("lng_terminal","Dahej")
    dis_ctries = parsed.get("disrupted_countries", [])
    region     = parsed.get("disrupted_region", "General Disruption")

    target_coords = PORT_COORDINATES.get(port,     [86.6, 20.2])
    source_coords = [50.111, 26.657]  # Ras Tanura, Saudi Arabia

    # Map region to realistic corridor risk
    region_lower = region.lower()
    if any(k in region_lower for k in ["red sea", "houthi", "bab", "aden"]):
        corridor_risk = 0.90
    elif any(k in region_lower for k in ["hormuz", "iran", "gulf"]):
        corridor_risk = 0.85
    elif any(k in region_lower for k in ["suez", "canal"]):
        corridor_risk = 0.75
    elif any(k in region_lower for k in ["russia", "sanction", "ukraine"]):
        corridor_risk = 0.65
    else:
        corridor_risk = 0.50

    result = {"status": "success", "commodity": commodity, "region": region, "deliberation_log": []}

    # ── [NETRA] Threat Characterization ───────────────────────────────────────
    result["deliberation_log"].append(
        f"[NETRA] Crisis detected: '{region}'. "
        f"Corridor risk computed at {round(corridor_risk*100, 0):.0f}%. "
        f"Affected commodity: {commodity.upper()}."
    )

    # ── [MARG] Price Shock Estimation ─────────────────────────────────────────
    result["price_shock"] = estimate_price_shock(corridor_risk)
    result["deliberation_log"].append(
        f"[MARG] VECM price model applied. "
        f"Brent shock: +${result['price_shock']['brent_shock_usd_bbl']}/bbl "
        f"(CI: {result['price_shock']['confidence_interval']}). "
        f"JKM LNG shock: +${result['price_shock']['jkm_shock_usd_mmbtu']}/MMBtu."
    )

    # ── Crude Branch ──────────────────────────────────────────────────────────
    if commodity in ("crude", "both") and c_deficit > 0:
        constraints = evaluate_infrastructure_constraints(c_deficit, port)
        if constraints.get("is_bottlenecked"):
            result["deliberation_log"].append(
                f"[MARG] Infrastructure assessment: {port} bottlenecked! "
                f"SPM cap: {constraints['spm_capacity']} MMT/d, Pipeline cap: {constraints['pipeline_capacity']} MMT/d. "
                f"Requesting {c_deficit} MMT/d exceeds physical limits."
            )
        else:
            result["deliberation_log"].append(
                f"[MARG] {port} infrastructure: CLEAR. Capacity sufficient."
            )

        assay_df = _load_assays()
        if assay_df.empty:
            assay_df = pd.DataFrame([
                {"name": "Arab Light", "API": 33.0, "Sulfur": 1.77, "TAN": 0.1,
                 "Route_Risk": 0.80, "Brent_Diff": -1.2},
            ])
        assay_df = assay_df.rename(columns={"name": "Crude_Name"})
        matched = match_crude_assays(refinery, 32.0, 1.5, 0.15, assay_df)

        # Upgrade 3: include AII penalty data in top crudes output
        aii_cols = ["Crude_Name", "Viability_Score", "AII_Penalty", "AII_Risk_Band", "AII_Note", "API_Delta", "Route_Risk"]
        available_cols = [c for c in aii_cols if c in matched.columns]
        top_crudes = matched[available_cols].head(3).to_dict("records")

        result["deliberation_log"].append(
            f"[RASAYAN] Scanned 22-grade global assay DB. "
            f"Best replacement for {refinery}: {top_crudes[0]['Crude_Name']} "
            f"(Viability Score: {round(top_crudes[0]['Viability_Score'], 2)} | "
            f"AII Risk: {top_crudes[0].get('AII_Risk_Band', 'N/A')})."
        )

        drawdown = solve_drawdown(c_deficit, Phase.PHASE_1)
        drawdown_total = drawdown.get("Total_Covered", c_deficit)
        unmet = drawdown.get("Unmet_Deficit_MMT", 0)
        if unmet > 0.01:
            result["deliberation_log"].append(
                f"[KOSH] ⚠ CAPACITY GAP: Physical reserve capacity exhausted. "
                f"Max drawdown: {round(drawdown_total, 2)} MMT. Unmet deficit: {round(unmet, 2)} MMT — "
                f"requires emergency spot procurement."
            )
        else:
            result["deliberation_log"].append(
                f"[KOSH] Phase I MILP solver completed. "
                f"Total drawdown plan: {round(drawdown_total, 2)} MMT. "
                f"OMC contribution: {round(c_deficit*0.6, 2)} MMT | ISPRL: {round(c_deficit*0.4, 2)} MMT."
            )

        route_info = calculate_maritime_route(source_coords, target_coords)
        reroute    = calculate_rerouting_delay("VLCC")

        # Run-rate impact & recovery timeline
        rr_impact = calculate_run_rate_impact(c_deficit, refinery)
        timeline  = generate_recovery_timeline(c_deficit, port, route_info.get("distance_nm", 4000), "crude")

        result["crude"] = {
            "scenario_parsed": {
                "deficit_mmt": c_deficit, "refinery": refinery, "port": port,
                "coordinates": target_coords, "source_coordinates": source_coords,
                "route_geometry": route_info.get("route_geometry"),
                "distance_nm":    round(route_info.get("distance_nm", 0), 0),
            },
            "agent2_infrastructure_check": constraints,
            "agent3_crude_alternatives":   top_crudes,
            "agent4_drawdown_plan":        drawdown,
            "rerouting":                   reroute,
            "run_rate_impact":             rr_impact,
            "recovery_timeline":           timeline,
        }


    # ── Gas Branch ────────────────────────────────────────────────────────────
    if commodity in ("gas", "both") and g_deficit > 0:
        supplier_match = match_lng_suppliers(g_deficit, terminal, disrupted_countries=dis_ctries)
        if supplier_match.get("top_suppliers"):
            s0 = supplier_match["top_suppliers"][0]
            result["deliberation_log"].append(
                f"[RASAYAN] LNG market scan complete. "
                f"Top supplier: {s0['name']} ({s0['country']}) — "
                f"Methane {s0['methane_pct']}%, Risk: {s0.get('risk', 'Low')}."
            )

        regasif_plan = calculate_regasification_plan(g_deficit)
        gas_drawdown = solve_gas_drawdown(g_deficit, disrupted_terminals=[])
        result["deliberation_log"].append(
            f"[KOSH] Gas distribution plan: "
            f"{g_deficit} MMSCMD across {len(regasif_plan.get('terminal_plan', []))} LNG terminals. "
            f"Shortfall: {regasif_plan.get('shortfall_mmscmd', 0)} MMSCMD (requires domestic field ramp-up)."
        )

        lng_source  = [51.55, 25.90]   # Ras Laffan, Qatar
        lng_target  = PORT_COORDINATES.get(terminal, [72.5, 21.7])
        lng_route   = calculate_maritime_route(lng_source, lng_target)
        reroute_lng = calculate_rerouting_delay("LNG_QFLEX")
        timeline_gas = generate_recovery_timeline(g_deficit, terminal, lng_route.get("distance_nm", 3500), "gas")

        result["gas"] = {
            "scenario_parsed": {
                "deficit_mmscmd": g_deficit, "terminal": terminal,
                "coordinates": lng_target, "source_coordinates": lng_source,
                "route_geometry": lng_route.get("route_geometry"),
                "distance_nm":    round(lng_route.get("distance_nm", 0), 0),
                "disrupted_countries": dis_ctries,
            },
            "agent3_lng_suppliers":       supplier_match,
            "agent4_regasification_plan": regasif_plan,
            "agent4_gas_drawdown":        gas_drawdown,
            "rerouting":                  reroute_lng,
            "prices":                     PRICE_DATA,
            "recovery_timeline":          timeline_gas,
        }

    # ── [CHAKRA] Red Team Assessment ──────────────────────────────────────────
    result["deliberation_log"].append(
        "[CHAKRA] Red-teaming the proposed plan for hidden vulnerabilities..."
    )
    critic_report = evaluate_plan_vulnerabilities(result)
    result["agent6_critic"] = critic_report
    n_warn = len(critic_report["warnings"])
    if n_warn:
        sev_list = [w["severity"] for w in critic_report["warnings"]]
        result["deliberation_log"].append(
            f"[CHAKRA] ALERT: {n_warn} vulnerabilities found "
            f"({sev_list.count('CRITICAL')} CRITICAL, {sev_list.count('HIGH')} HIGH, "
            f"{sev_list.count('MEDIUM')} MEDIUM). Review before authorizing."
        )
    else:
        result["deliberation_log"].append(
            "[CHAKRA] Plan verified. No critical vulnerabilities detected. Safe to authorize."
        )

    # ── [KAUTILYA] Composite Supply Chain Risk Index ──────────────────────────
    is_bottlenecked = result.get("crude", {}).get("agent2_infrastructure_check", {}).get("is_bottlenecked", False)
    result["supply_risk_index"] = compute_supply_risk_index(
        corridor_risk=corridor_risk,
        is_bottlenecked=is_bottlenecked,
        critic_warning_count=n_warn,
        deficit_mmt=max(c_deficit, g_deficit * 0.3)  # normalize gas to crude-equivalent
    )
    result["deliberation_log"].append(
        f"[KAUTILYA] Composite Supply Chain Risk Index: "
        f"{result['supply_risk_index']['score']}/100 "
        f"({result['supply_risk_index']['band']} RISK). "
        f"Directive package ready for authorization."
    )

    # ── Upgrade 5: Persist simulation snapshot ────────────────────────────────
    snapshot_id = save_snapshot(result)
    if snapshot_id:
        result["snapshot_id"] = snapshot_id
        logger.info(f"Simulation snapshot saved: {snapshot_id}")

    return result


# ─── Vessel Tracking Endpoint ─────────────────────────────────────────────────
@app.get("/api/v1/vessels")
async def get_vessels():
    """
    Fetch persistent strategic fleet and live AIS vessel positions with MARG dead-reckoning enrichment.
    """
    enriched = enrich_vessels_with_dead_reckoning(_LIVE_VESSELS, stale_threshold_seconds=60)
    return {
        "status": "success",
        "source": "strategic_fleet_telemetry",
        "count": len(enriched),
        "vessels": enriched
    }

# ─── Upgrade 5: Snapshot / Session Endpoints ──────────────────────────────────
@app.get("/api/v1/snapshots")
async def get_snapshots():
    """List the last 10 simulation snapshots for the War Games Archive."""
    snapshots = list_snapshots(limit=10)
    latest_age = get_age_of_latest_seconds()
    return {
        "status": "success",
        "snapshots": snapshots,
        "latest_age_seconds": latest_age,
    }

@app.get("/api/v1/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """Retrieve a specific snapshot by ID for time-travel replay."""
    data = get_snapshot_by_id(snapshot_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Snapshot '{snapshot_id}' not found.")
    return {"status": "success", "snapshot": data}

# ─── Remaining Endpoints ──────────────────────────────────────────────────────
@app.post("/api/v1/trigger-agent4")
async def trigger_agent4(req: DeficitRequest):
    phase_enum = Phase.PHASE_1 if req.phase == 1 else Phase.PHASE_2
    return {"status": "success", "data": solve_drawdown(req.daily_deficit_mmt, phase_enum)}

@app.post("/api/v1/cloud-llm-intel")
async def process_intelligence(req: IntelRequest):
    ukmto = fetch_ukmto_incidents(incident_types=req.incident_types)
    gdelt  = fetch_gdelt_data(query=req.query, max_records=8)
    # Upgrade 1: Build incident graph (escalation chains)
    incident_chains = build_incident_graph(ukmto, gdelt)
    return {
        "status": "success",
        "raw_intelligence": {"UKMTO": ukmto, "GDELT": gdelt},
        "incident_chains": incident_chains,
    }

@app.post("/api/v1/portwatch")
async def get_portwatch_data(req: PortWatchRequest):
    data = fetch_imf_portwatch(req.port_id, req.start_date, req.end_date, req.metric)
    return {"status":"success","data":data}

@app.post("/api/v1/route")
async def get_route(req: RouteRequest):
    return {"status":"success","data":calculate_maritime_route(req.origin, req.dest)}

@app.post("/api/v1/generate-audit")
async def generate_audit(req: DirectiveRequest):
    if req.authorization_token != "AUTHORIZE_DIRECTIVE":
        raise HTTPException(status_code=403, detail="Invalid token")
    return generate_audit_package(req.deficit_mmt, req.phase, req.drawdown_plan)

@app.get("/api/v1/prices")
async def get_prices():
    return {"status":"success","prices":PRICE_DATA}

@app.get("/api/v1/lng-terminals")
async def get_lng_terminals():
    return {"status":"success","terminals":LNG_TERMINALS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
