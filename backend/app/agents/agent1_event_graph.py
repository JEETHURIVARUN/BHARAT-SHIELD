"""
NETRA — Event-Graph Memory & Temporal Decay
Incident chaining and exponential decay for maritime intelligence.
Uses location-cluster matching + time-window grouping + Risk(t) decay scoring.
"""
import datetime
import math
import logging
import re
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ─── Location Cluster Mapping ─────────────────────────────────────────────────
# Maps location keywords → canonical corridor name + risk weight
LOCATION_CLUSTERS = {
    "red sea":          {"corridor": "Bab-el-Mandeb / Red Sea",     "base_risk": 0.90},
    "houthi":           {"corridor": "Bab-el-Mandeb / Red Sea",     "base_risk": 0.90},
    "bab el mandeb":    {"corridor": "Bab-el-Mandeb / Red Sea",     "base_risk": 0.90},
    "bab-el-mandeb":    {"corridor": "Bab-el-Mandeb / Red Sea",     "base_risk": 0.90},
    "aden":             {"corridor": "Gulf of Aden",                  "base_risk": 0.80},
    "gulf of aden":     {"corridor": "Gulf of Aden",                  "base_risk": 0.80},
    "hormuz":           {"corridor": "Strait of Hormuz",             "base_risk": 0.85},
    "strait of hormuz": {"corridor": "Strait of Hormuz",             "base_risk": 0.85},
    "fujairah":         {"corridor": "Strait of Hormuz",             "base_risk": 0.82},
    "gulf of oman":     {"corridor": "Gulf of Oman",                  "base_risk": 0.78},
    "suez":             {"corridor": "Suez Canal",                    "base_risk": 0.75},
    "suez canal":       {"corridor": "Suez Canal",                    "base_risk": 0.75},
    "malacca":          {"corridor": "Strait of Malacca",            "base_risk": 0.60},
    "singapore":        {"corridor": "Strait of Malacca",            "base_risk": 0.55},
    "persian gulf":     {"corridor": "Persian Gulf",                  "base_risk": 0.80},
    "arabian sea":      {"corridor": "Arabian Sea",                   "base_risk": 0.55},
    "india":            {"corridor": "Indian Ocean",                  "base_risk": 0.30},
    "somalia":          {"corridor": "Gulf of Aden",                  "base_risk": 0.85},
}

# ─── Severity weights for escalation scoring ──────────────────────────────────
SEVERITY_WEIGHTS = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.50, "LOW": 0.25}

# ─── Chain merging: events in the same corridor within this window are linked ─
CHAIN_WINDOW_HOURS = 12.0


def _extract_corridor(text: str) -> Optional[str]:
    """
    Fuzzy-match text against location cluster keywords.
    Returns canonical corridor name or None.
    """
    text_lower = text.lower()
    # Sort by length descending so longer phrases match before substrings
    for keyword in sorted(LOCATION_CLUSTERS.keys(), key=len, reverse=True):
        if keyword in text_lower:
            return LOCATION_CLUSTERS[keyword]["corridor"]
    return None


def _extract_base_risk(text: str) -> float:
    """Return the base risk score for the first corridor matched in text."""
    text_lower = text.lower()
    for keyword in sorted(LOCATION_CLUSTERS.keys(), key=len, reverse=True):
        if keyword in text_lower:
            return LOCATION_CLUSTERS[keyword]["base_risk"]
    return 0.40  # Default moderate risk


def _decay_risk(base_risk: float, event_time_iso: str, lambda_decay: float = 0.05) -> float:
    """
    Risk(t) = base_risk × e^(-λ × Δhours)
    λ=0.05 → ~50% decay after ~14 hours (suitable for maritime incidents).
    """
    try:
        t0 = datetime.datetime.fromisoformat(
            event_time_iso.replace("Z", "+00:00")
        )
        now   = datetime.datetime.now(datetime.timezone.utc)
        delta = (now - t0).total_seconds() / 3600.0
        risk  = base_risk * math.exp(-lambda_decay * delta)
        return round(max(0.0, min(1.0, risk)), 4)
    except Exception:
        return base_risk


def _parse_timestamp(ts: str) -> datetime.datetime:
    """Parse ISO or RFC 2822 timestamps into UTC datetime."""
    if not ts:
        return datetime.datetime.now(datetime.timezone.utc)
    try:
        # Try ISO 8601 first
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        pass
    try:
        # RFC 2822 (RSS format: "Thu, 18 Jan 2024 08:14:00 GMT")
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(ts)
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


def build_incident_graph(
    ukmto_incidents: List[Dict],
    gdelt_articles: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Merge UKMTO incidents and GDELT articles into Escalation Chains.
    
    Algorithm:
    1. Assign each event a canonical corridor via location cluster matching.
    2. Group events with the same corridor within CHAIN_WINDOW_HOURS.
    3. Compute cumulative decayed risk score per chain.
    4. Return chains sorted by risk (highest first).

    Returns list of chain dicts:
    {
        "chain_id":       str,
        "corridor":       str,
        "event_count":    int,
        "time_span_hours":float,
        "first_seen":     str (ISO),
        "last_seen":      str (ISO),
        "decayed_risk":   float,
        "peak_severity":  str,
        "events":         List[Dict],
        "is_escalating":  bool,    # True if risk is rising (recent events after older ones)
        "chain_label":    str,     # Human-readable summary
    }
    """
    # ── Step 1: Normalize all events into a common format ─────────────────────
    all_events = []

    for inc in ukmto_incidents:
        text = f"{inc.get('type','')} {inc.get('location','')} {inc.get('corridor','')} {inc.get('raw_details','')}"
        corridor = _extract_corridor(text) or inc.get("corridor", "Unknown")
        ts_str   = inc.get("timestamp", "")
        all_events.append({
            "source":    "UKMTO",
            "type":      inc.get("type", "Maritime Incident"),
            "severity":  inc.get("severity", "MEDIUM"),
            "title":     inc.get("raw_details", "")[:120],
            "location":  inc.get("location", ""),
            "corridor":  corridor,
            "timestamp": ts_str,
            "parsed_dt": _parse_timestamp(ts_str),
            "base_risk": _extract_base_risk(text),
        })

    for art in gdelt_articles:
        text = f"{art.get('title','')} {art.get('domain','')} {art.get('sourcecountry','')}"
        corridor = _extract_corridor(text)
        if not corridor:
            continue  # Skip GDELT articles we can't locate
        ts_str   = art.get("seendate", "") or ""
        sev_word = any(w in text.lower() for w in ["attack", "explosion", "missile", "hijack", "seized"])
        severity = "HIGH" if sev_word else "MEDIUM"
        all_events.append({
            "source":    "GDELT",
            "type":      "Press Report",
            "severity":  severity,
            "title":     art.get("title", "")[:120],
            "location":  art.get("sourcecountry", ""),
            "corridor":  corridor,
            "timestamp": ts_str,
            "parsed_dt": _parse_timestamp(ts_str),
            "base_risk": _extract_base_risk(text),
            "url":       art.get("url", ""),
            "tone":      art.get("tone", "0"),
        })

    # ── Step 2: Group into chains by corridor + time window ───────────────────
    # Sort by (corridor, time)
    all_events.sort(key=lambda e: (e["corridor"], e["parsed_dt"]))

    chains: Dict[str, Dict] = {}  # key: corridor

    for event in all_events:
        corridor = event["corridor"]

        if corridor not in chains:
            chains[corridor] = {
                "chain_id":    corridor.lower().replace(" ", "_").replace("/", "_")[:20],
                "corridor":    corridor,
                "events":      [],
                "first_dt":    event["parsed_dt"],
                "last_dt":     event["parsed_dt"],
            }

        chain = chains[corridor]
        # Check time window — if event is within CHAIN_WINDOW_HOURS of last event, add to chain
        hours_diff = abs((event["parsed_dt"] - chain["last_dt"]).total_seconds()) / 3600.0
        if hours_diff <= CHAIN_WINDOW_HOURS or not chain["events"]:
            chain["events"].append(event)
            chain["last_dt"] = max(chain["last_dt"], event["parsed_dt"])
            chain["first_dt"] = min(chain["first_dt"], event["parsed_dt"])
        else:
            # New time window — reset chain for this corridor (treat as new incident cluster)
            chain["events"].append(event)
            chain["last_dt"] = event["parsed_dt"]

    # ── Step 3: Score and annotate each chain ─────────────────────────────────
    result = []
    for corridor, chain in chains.items():
        events     = chain["events"]
        if not events:
            continue

        first_dt   = chain["first_dt"]
        last_dt    = chain["last_dt"]
        span_hours = round(abs((last_dt - first_dt).total_seconds()) / 3600.0, 1)

        # Cumulative decayed risk: sum of each event's decayed risk (capped at 1.0)
        total_risk = 0.0
        for ev in events:
            sev_w    = SEVERITY_WEIGHTS.get(ev["severity"], 0.5)
            raw_risk = ev["base_risk"] * sev_w
            decayed  = _decay_risk(raw_risk, ev["parsed_dt"].isoformat())
            total_risk += decayed
        cumulative_risk = round(min(1.0, total_risk), 4)

        # Peak severity across all events
        sev_order  = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        severities = [ev["severity"] for ev in events]
        peak_sev   = next((s for s in sev_order if s in severities), "MEDIUM")

        # Is escalating? True if events are arriving more frequently (last 2 closer than first 2)
        is_escalating = False
        if len(events) >= 3:
            gap_first = abs((events[1]["parsed_dt"] - events[0]["parsed_dt"]).total_seconds())
            gap_last  = abs((events[-1]["parsed_dt"] - events[-2]["parsed_dt"]).total_seconds())
            is_escalating = gap_last < gap_first  # gaps shrinking → escalation

        # Chain label
        n = len(events)
        label = (
            f"{n} linked event{'s' if n>1 else ''} in {corridor}"
            + (f" over {span_hours:.1f}h" if span_hours > 0.1 else "")
            + (" — ESCALATING" if is_escalating else "")
        )

        result.append({
            "chain_id":        chain["chain_id"],
            "corridor":        corridor,
            "event_count":     n,
            "time_span_hours": span_hours,
            "first_seen":      first_dt.isoformat(),
            "last_seen":       last_dt.isoformat(),
            "decayed_risk":    cumulative_risk,
            "peak_severity":   peak_sev,
            "is_escalating":   is_escalating,
            "chain_label":     label,
            "events":          events,
        })

    # Sort by risk descending
    result.sort(key=lambda c: c["decayed_risk"], reverse=True)
    return result


if __name__ == "__main__":
    mock_ukmto = [
        {"type":"Attack",  "severity":"HIGH",     "location":"Red Sea (15°N, 43°E)",       "corridor":"Bab-el-Mandeb", "raw_details":"Drone sighted off Fujairah",       "timestamp":"2024-01-18T08:00:00Z"},
        {"type":"Boarding","severity":"CRITICAL",  "location":"Red Sea (14°N, 43°E)",       "corridor":"Bab-el-Mandeb", "raw_details":"Tanker explosion near Fujairah",   "timestamp":"2024-01-18T11:00:00Z"},
    ]
    mock_gdelt = [
        {"title":"Houthi drone hits oil tanker in Red Sea", "seendate":"2024-01-18","sourcecountry":"UK","domain":"bbc.com","url":"","tone":"-6.2"},
        {"title":"India reroutes crude shipments via Cape of Good Hope", "seendate":"2024-01-17","sourcecountry":"India","domain":"economictimes.com","url":"","tone":"-4.0"},
    ]
    chains = build_incident_graph(mock_ukmto, mock_gdelt)
    for c in chains:
        print(f"Chain: {c['corridor']} | Events: {c['event_count']} | Risk: {c['decayed_risk']} | Label: {c['chain_label']}")
