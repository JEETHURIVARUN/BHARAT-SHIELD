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
