"""
MARG — Dead Reckoning Vessel Extrapolation
Cinematic physics-based Dead Reckoning when AIS telemetry drops or is jammed. (dark zone / GPS spoofing).
Uses Mercator sailing formula.
"""
import math
import datetime
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Vessel-type average speeds (knots) for fallback dead reckoning
VESSEL_TYPE_SOG = {
    "VLCC Tanker":    12.5,
    "Suezmax Tanker": 13.0,
    "Aframax Tanker": 13.5,
    "LNG Carrier":    17.0,
    "Tanker":         12.0,
}

# MMSI prefix (MID) mapping to Country & Geopolitical Tag
COUNTRY_MIDS = {
    "419": {"country": "India", "flag": "🇮🇳", "category": "Indian Sovereign Fleet", "strategic": True},
    "403": {"country": "Saudi Arabia", "flag": "🇸🇦", "category": "Allied Energy Partner", "strategic": True},
    "470": {"country": "UAE", "flag": "🇦🇪", "category": "Allied Energy Partner", "strategic": True},
    "471": {"country": "UAE", "flag": "🇦🇪", "category": "Allied Energy Partner", "strategic": True},
    "466": {"country": "Qatar", "flag": "🇶🇦", "category": "LNG Supply Partner", "strategic": True},
    "447": {"country": "Kuwait", "flag": "🇰🇼", "category": "Allied Energy Partner", "strategic": True},
    "461": {"country": "Oman", "flag": "🇴🇲", "category": "Strategic Maritime Partner", "strategic": True},
    "425": {"country": "Iraq", "flag": "🇮🇶", "category": "Crude Supply Partner", "strategic": True},
    "408": {"country": "Bahrain", "flag": "🇧🇭", "category": "Gulf Maritime Partner", "strategic": True},
    "273": {"country": "Russia", "flag": "🇷🇺", "category": "Strategic Energy Partner", "strategic": True},
    "338": {"country": "USA", "flag": "🇺🇸", "category": "Strategic Partner", "strategic": True},
    "366": {"country": "USA", "flag": "🇺🇸", "category": "Strategic Partner", "strategic": True},
    "367": {"country": "USA", "flag": "🇺🇸", "category": "Strategic Partner", "strategic": True},
    "368": {"country": "USA", "flag": "🇺🇸", "category": "Strategic Partner", "strategic": True},
    "369": {"country": "USA", "flag": "🇺🇸", "category": "Strategic Partner", "strategic": True},
    "563": {"country": "Singapore", "flag": "🇸🇬", "category": "Malacca Strait Partner", "strategic": True},
    "564": {"country": "Singapore", "flag": "🇸🇬", "category": "Malacca Strait Partner", "strategic": True},
    "565": {"country": "Singapore", "flag": "🇸🇬", "category": "Malacca Strait Partner", "strategic": True},
    "566": {"country": "Singapore", "flag": "🇸🇬", "category": "Malacca Strait Partner", "strategic": True},
    "503": {"country": "Australia", "flag": "🇦🇺", "category": "LNG Supply Partner", "strategic": True},
    "412": {"country": "China", "flag": "🇨🇳", "category": "Security Monitoring", "strategic": True},
    "413": {"country": "China", "flag": "🇨🇳", "category": "Security Monitoring", "strategic": True},
    "414": {"country": "China", "flag": "🇨🇳", "category": "Security Monitoring", "strategic": True},
    "463": {"country": "Pakistan", "flag": "🇵🇰", "category": "Neighbouring Security", "strategic": True},
    "422": {"country": "Iran", "flag": "🇮🇷", "category": "Hormuz Regional Security", "strategic": True},
    "473": {"country": "Yemen", "flag": "🇾🇪", "category": "Red Sea Security", "strategic": True},
    "475": {"country": "Yemen", "flag": "🇾🇪", "category": "Red Sea Security", "strategic": True},
    "417": {"country": "Sri Lanka", "flag": "🇱🇰", "category": "Neighbouring Maritime", "strategic": True},
    "405": {"country": "Bangladesh", "flag": "🇧🇩", "category": "Neighbouring Maritime", "strategic": True},
    "455": {"country": "Maldives", "flag": "🇲🇻", "category": "Indian Ocean Security", "strategic": True},
    "506": {"country": "Myanmar", "flag": "🇲🇲", "category": "Bay of Bengal", "strategic": True},
    # International tanker registries carrying Indian crude/LNG:
    "636": {"country": "Liberia (Charter)", "flag": "🇱🇷", "category": "Energy Import Charter", "strategic": True},
    "538": {"country": "Marshall Islands (Charter)", "flag": "🇲🇭", "category": "Energy Import Charter", "strategic": True},
    "351": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "352": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "353": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "354": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "355": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "356": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "357": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "370": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "371": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "372": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "373": {"country": "Panama (Charter)", "flag": "🇵🇦", "category": "Energy Import Charter", "strategic": True},
    "308": {"country": "Bahamas (Charter)", "flag": "🇧🇸", "category": "Energy Import Charter", "strategic": True},
    "309": {"country": "Bahamas (Charter)", "flag": "🇧🇸", "category": "Energy Import Charter", "strategic": True},
    "311": {"country": "Bahamas (Charter)", "flag": "🇧🇸", "category": "Energy Import Charter", "strategic": True},
    "215": {"country": "Malta (Charter)", "flag": "🇲🇹", "category": "Energy Import Charter", "strategic": True},
    "229": {"country": "Malta (Charter)", "flag": "🇲🇹", "category": "Energy Import Charter", "strategic": True},
    "248": {"country": "Malta (Charter)", "flag": "🇲🇹", "category": "Energy Import Charter", "strategic": True},
    "249": {"country": "Malta (Charter)", "flag": "🇲🇹", "category": "Energy Import Charter", "strategic": True},
    "209": {"country": "Cyprus (Charter)", "flag": "🇨🇾", "category": "Energy Import Charter", "strategic": True},
    "210": {"country": "Cyprus (Charter)", "flag": "🇨🇾", "category": "Energy Import Charter", "strategic": True},
    "212": {"country": "Cyprus (Charter)", "flag": "🇨🇾", "category": "Energy Import Charter", "strategic": True},
    "237": {"country": "Greece (Charter)", "flag": "🇬🇷", "category": "Energy Import Charter", "strategic": True},
    "239": {"country": "Greece (Charter)", "flag": "🇬🇷", "category": "Energy Import Charter", "strategic": True},
    "240": {"country": "Greece (Charter)", "flag": "🇬🇷", "category": "Energy Import Charter", "strategic": True},
    "241": {"country": "Greece (Charter)", "flag": "🇬🇷", "category": "Energy Import Charter", "strategic": True},
}

def get_vessel_geopolitics(mmsi: str) -> Dict[str, str]:
    """Identify flag, country, and strategic category from vessel MMSI."""
    if not mmsi or len(mmsi) < 3:
        return {"country": "International", "flag": "🌐", "category": "General Maritime", "strategic": False}
    mid = str(mmsi)[:3]
    return COUNTRY_MIDS.get(mid, {"country": "International", "flag": "🌐", "category": "General Maritime", "strategic": False})

def is_in_strategic_theater(lon: float, lat: float) -> bool:
    """
    Check if coordinates fall within India's strategic energy maritime theater:
    Indian Ocean, Arabian Sea, Bay of Bengal, Persian Gulf, Red Sea, Strait of Malacca.
    """
    return (30.0 <= lon <= 108.0) and (-20.0 <= lat <= 35.0)

# AIS dark-zone corridors — regions with known GPS spoofing/denial
DARK_ZONE_CORRIDORS = [
    {"name": "Strait of Hormuz GPS Denial Zone", "bbox": [55.0, 24.0, 59.0, 27.0]},
    {"name": "Red Sea Southern Corridor",         "bbox": [41.0, 12.0, 45.0, 16.0]},
    {"name": "Gulf of Oman Spoofing Zone",        "bbox": [56.5, 21.0, 60.5, 25.0]},
]


def _is_in_dark_zone(lon: float, lat: float) -> str | None:
    """Check if a coordinate is within a known AIS dark zone."""
    for zone in DARK_ZONE_CORRIDORS:
        b = zone["bbox"]
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
            return zone["name"]
    return None


def extrapolate_position(
    last_lon: float,
    last_lat: float,
    heading_deg: float,
    sog_knots: float,
    elapsed_seconds: float
) -> Tuple[float, float]:
    """
    Dead Reckoning via Mercator sailing formula.
    Projects vessel position forward from last known position.

    Args:
        last_lon:        Last known longitude (degrees)
        last_lat:        Last known latitude (degrees)
        heading_deg:     True heading (0–360°)
        sog_knots:       Speed over ground (knots)
        elapsed_seconds: Seconds since last AIS fix

    Returns:
        (new_lon, new_lat) as floats
    """
    if elapsed_seconds <= 0 or sog_knots <= 0:
        return last_lon, last_lat

    R_nm = 3440.065  # Earth radius in nautical miles

    # Distance traveled in nautical miles
    distance_nm = sog_knots * (elapsed_seconds / 3600.0)

    heading_rad = math.radians(heading_deg)
    lat_rad     = math.radians(last_lat)

    # Angular distance
    delta = distance_nm / R_nm

    # Spherical dead reckoning (good for distances < 1000nm)
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(delta) +
        math.cos(lat_rad) * math.sin(delta) * math.cos(heading_rad)
    )
    new_lon_rad = math.radians(last_lon) + math.atan2(
        math.sin(heading_rad) * math.sin(delta) * math.cos(lat_rad),
        math.cos(delta) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )

    new_lat = round(math.degrees(new_lat_rad), 6)
    new_lon = round(math.degrees(new_lon_rad), 6)

    # Clamp to valid range
    new_lat = max(-90.0, min(90.0, new_lat))
    new_lon = ((new_lon + 180) % 360) - 180

    return new_lon, new_lat


def enrich_vessels_with_dead_reckoning(
    live_vessels: Dict[str, dict],
    stale_threshold_seconds: int = 90
) -> list:
    """
    Iterate over _LIVE_VESSELS, extrapolate stale vessels, and annotate each.

    Args:
        live_vessels:             The _LIVE_VESSELS dict from main.py
        stale_threshold_seconds:  Seconds after which a vessel is considered stale

    Returns:
        List of vessel dicts with position_type and extrapolated_seconds fields added.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    enriched = []

    for mmsi, v in live_vessels.items():
        vessel = v.copy()

        last_update_str = vessel.get("last_update_utc")
        if not last_update_str:
            vessel["position_type"] = "live"
            vessel["extrapolated_seconds"] = 0
            enriched.append(vessel)
            continue

        try:
            last_update = datetime.datetime.fromisoformat(last_update_str)
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_update).total_seconds()
        except Exception:
            vessel["position_type"] = "live"
            vessel["extrapolated_seconds"] = 0
            enriched.append(vessel)
            continue

        if elapsed > stale_threshold_seconds:
            # Use stored SOG, fall back to vessel-type average
            sog = vessel.get("speed", 0)
            if sog < 0.5:
                sog = VESSEL_TYPE_SOG.get(vessel.get("type", "Tanker"), 12.0)
            heading = vessel.get("heading", 0) or 0

            orig_lon, orig_lat = vessel["lon"], vessel["lat"]
            new_lon, new_lat = extrapolate_position(
                orig_lon, orig_lat, heading, sog, elapsed
            )
            vessel["lon"] = new_lon
            vessel["lat"] = new_lat
            vessel["position_type"] = "dead_reckoned"
            vessel["extrapolated_seconds"] = int(elapsed)
            vessel["extrapolated_nm"] = round(sog * (elapsed / 3600), 1)
            vessel["original_lon"] = orig_lon
            vessel["original_lat"] = orig_lat

            # Check if vessel is in a dark zone
            dark_zone = _is_in_dark_zone(new_lon, new_lat)
            vessel["dark_zone"] = dark_zone
        else:
            vessel["position_type"] = "live"
            vessel["extrapolated_seconds"] = 0
            vessel["dark_zone"] = _is_in_dark_zone(vessel["lon"], vessel["lat"])

        # Add Geopolitical & Strategic Alignment tags
        geo = get_vessel_geopolitics(mmsi)
        vessel["country"] = geo.get("country", "International")
        vessel["flag"] = geo.get("flag", "🌐")
        vessel["category"] = geo.get("category", "General Maritime")
        vessel["is_strategic"] = geo.get("strategic", False)

        enriched.append(vessel)

    return enriched


if __name__ == "__main__":
    # Test: VLCC heading SE at 12.5kn from Hormuz, 3 minutes stale
    lon, lat = extrapolate_position(
        last_lon=56.3, last_lat=26.2,
        heading_deg=135, sog_knots=12.5,
        elapsed_seconds=180  # 3 minutes
    )
    print(f"Dead Reckoned Position: lon={lon}, lat={lat}")

    # Test dark zone detection
    zone = _is_in_dark_zone(57.0, 25.5)
    print(f"Dark zone at 57°E, 25.5°N: {zone}")
