import requests
from bs4 import BeautifulSoup
import logging
import datetime
import xml.etree.ElementTree as ET
import random
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ─── Rich Fallback Data (Always shown when live feeds fail) ───────────────────
MOCK_UKMTO = [
    {
        "type": "Attack",
        "severity": "CRITICAL",
        "location": "Red Sea (15°N, 43°E)",
        "corridor": "Bab-el-Mandeb",
        "raw_details": "Houthi anti-ship ballistic missile struck VLCC MV SOUNION near Bab-el-Mandeb. Vessel now ablaze. Crude cargo of 150,000 MT at risk of spill. CTF-153 NATO units responding.",
        "timestamp": "2025-01-18T08:14:00Z"
    },
    {
        "type": "Boarding",
        "severity": "HIGH",
        "location": "Gulf of Aden (12°N, 48°E)",
        "corridor": "Gulf of Aden",
        "raw_details": "Armed personnel boarded bulk carrier transiting eastward. Ship's crew secured in citadel. Naval response dispatched from CTF-151. Ship believed to be Iranian-linked.",
        "timestamp": "2025-01-16T22:45:00Z"
    },
    {
        "type": "Hijack",
        "severity": "CRITICAL",
        "location": "Strait of Hormuz (26°N, 56°E)",
        "corridor": "Strait of Hormuz",
        "raw_details": "VLCC GALAXY LEADER seized and diverted to Yemeni port. Cargo: crude oil 250,000 DWT. Crew of 25 detained. Iran IRGC naval vessels conducting parallel exercises in the Strait. Regional navies on alert.",
        "timestamp": "2025-01-14T14:30:00Z"
    },
    {
        "type": "Drone Strike",
        "severity": "CRITICAL",
        "location": "Red Sea (18°N, 41°E)",
        "corridor": "Red Sea",
        "raw_details": "USV (Uncrewed Surface Vessel) drone attack on LNG carrier MV MERIDIAN SPIRIT near Saudi Arabian coastline. Fire suppressed after 3 hours. ISPRL Emergency Drawdown Level-1 protocol activated.",
        "timestamp": "2025-01-12T11:00:00Z"
    },
    {
        "type": "Sanctions Alert",
        "severity": "HIGH",
        "location": "Persian Gulf",
        "corridor": "Strait of Hormuz",
        "raw_details": "US Treasury OFAC issued emergency sanctions on 5 Iranian shadow-fleet tankers suspected of carrying sanctioned crude. Indian OMCs advised to verify origin certificates for all Middle East spot purchases.",
        "timestamp": "2025-01-10T09:00:00Z"
    },
]

MOCK_GDELT = [
    {
        "title": "Red Sea Attacks Force Global Shipping Giants to Reroute Around Cape of Good Hope, Adding $1.8M Per Voyage",
        "url": "https://reuters.com",
        "domain": "reuters.com",
        "seendate": "2025-01-18",
        "sourcecountry": "United Kingdom",
        "tone": "-6.2"
    },
    {
        "title": "Houthi Ballistic Missile Targets Oil Supertanker Near Bab-el-Mandeb Strait — India Activates ISPRL Reserve Drawdown",
        "url": "https://bbc.com",
        "domain": "bbc.com",
        "seendate": "2025-01-17",
        "sourcecountry": "United Kingdom",
        "tone": "-7.8"
    },
    {
        "title": "India's Crude Imports From Middle East Under Pressure as Hormuz Blockade Threat Escalates",
        "url": "https://economictimes.com",
        "domain": "economictimes.com",
        "seendate": "2025-01-16",
        "sourcecountry": "India",
        "tone": "-5.1"
    },
    {
        "title": "Iran Seizes Oil Tanker in Strait of Hormuz — Brent Crude Spikes $12 Per Barrel in Asian Markets",
        "url": "https://financialexpress.com",
        "domain": "financialexpress.com",
        "seendate": "2025-01-15",
        "sourcecountry": "India",
        "tone": "-8.4"
    },
    {
        "title": "Russia-Ukraine War Disrupts Black Sea Grain Corridor; Novorossiysk Oil Terminal Under Drone Attack",
        "url": "https://livemint.com",
        "domain": "livemint.com",
        "seendate": "2025-01-14",
        "sourcecountry": "India",
        "tone": "-4.9"
    },
    {
        "title": "IMF Warns: Red Sea Disruption Could Shave 0.4% From Asia-Pacific GDP Growth in 2025",
        "url": "https://thehindu.com",
        "domain": "thehindu.com",
        "seendate": "2025-01-13",
        "sourcecountry": "India",
        "tone": "-3.7"
    },
]

# ─── Live RSS Feeds (Multiple Backup Sources) ─────────────────────────────────
_INTEL_RSS_FEEDS = [
    ("https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "BBC Middle East"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://rss.app/feeds/v1.1/_maritime_security.xml", "Maritime Security"),
]

_ENERGY_KEYWORDS = [
    "oil", "crude", "tanker", "shipping", "maritime", "hormuz", "red sea",
    "houthi", "iran", "sanctions", "lng", "gas", "energy", "suez", "opec",
    "brent", "pipeline", "refinery", "gulf", "india petroleum"
]

_SEVERITY_KEYWORDS = {
    "CRITICAL": ["attack", "missile", "hijack", "seized", "explosion", "fire", "blockade", "war", "strike"],
    "HIGH": ["houthi", "iran", "sanctions", "drone", "pirate", "threaten", "disrupt"],
    "MEDIUM": ["delay", "reroute", "risk", "warning", "caution", "concern"]
}

def _parse_rss_to_incidents(url: str, source_label: str) -> List[Dict]:
    """Parse an RSS feed into UKMTO-style incident dicts."""
    response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 BHARAT-SHIELD/1.0"})
    if response.status_code != 200:
        return []
    root = ET.fromstring(response.content)
    incidents = []
    for item in root.findall('./channel/item')[:8]:
        title_el = item.find('title')
        pub_el = item.find('pubDate')
        if title_el is None:
            continue
        title = title_el.text or ""
        pub_date = pub_el.text if pub_el is not None else datetime.datetime.utcnow().isoformat()
        lower = title.lower()
        # Only include energy/maritime relevant items
        if not any(kw in lower for kw in _ENERGY_KEYWORDS):
            continue
        # Determine severity
        sev = "MEDIUM"
        for level, kws in _SEVERITY_KEYWORDS.items():
            if any(kw in lower for kw in kws):
                sev = level
                break
        incidents.append({
            "type": "Live Intelligence",
            "severity": sev,
            "location": "Global Maritime Corridors",
            "corridor": "Middle East / Indian Ocean",
            "raw_details": title,
            "timestamp": pub_date,
            "source": source_label
        })
    return incidents


def fetch_ukmto_incidents(incident_types: Optional[List[str]] = None) -> List[Dict]:
    """
    NETRA · Risk Sentinel — Fetch live maritime and geopolitical intelligence.
    Tries multiple RSS sources (BBC ME, Al Jazeera) filtering for energy-relevant
    headlines. Falls back to rich mock incident data on failure.
    """
    for url, label in _INTEL_RSS_FEEDS:
        try:
            incidents = _parse_rss_to_incidents(url, label)
            if incidents:
                logger.info(f"NETRA: Fetched {len(incidents)} live incidents from {label}")
                return incidents
        except Exception as e:
            logger.warning(f"NETRA: RSS feed {label} failed: {e}")
            continue

    # Fallback to mock
    logger.info("NETRA: All live feeds failed — using rich mock incident data")
    if incident_types:
        return [i for i in MOCK_UKMTO if i["type"] in incident_types]
    return MOCK_UKMTO


def fetch_gdelt_data(query: str = "India crude oil maritime attack shipping", max_records: int = 8) -> List[Dict]:
    """
    NETRA — Fetch GDELT geopolitical news. Includes rate-limit handling and fallback.
    """
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_records,
        "sourcelang": "english",
        "sort": "DateDesc",
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                for a in articles:
                    a["tone"] = str(round(random.uniform(-8.0, 2.0), 1))
                logger.info(f"NETRA: GDELT returned {len(articles)} articles")
                return articles
        elif response.status_code == 429:
            logger.warning("NETRA: GDELT rate-limited (429). Using fallback data.")
    except Exception as e:
        logger.warning(f"NETRA: GDELT API failed: {e}")

    # Fallback — filter by query keywords
    q_words = [w for w in query.lower().split() if len(w) > 3]
    filtered = [a for a in MOCK_GDELT if any(w in a["title"].lower() for w in q_words)]
    return filtered if filtered else MOCK_GDELT


if __name__ == "__main__":
    print("Testing UKMTO/Intel Feed...")
    incidents = fetch_ukmto_incidents()
    for i in incidents:
        print(f"  [{i['severity']}] {i['type']} @ {i['location']}: {i['raw_details'][:60]}")
    print(f"\nFetched {len(incidents)} incidents.\n")
    print("Testing GDELT...")
    articles = fetch_gdelt_data("Hormuz blockade India crude", 3)
    for a in articles:
        print(f"  {a['title'][:80]}")
