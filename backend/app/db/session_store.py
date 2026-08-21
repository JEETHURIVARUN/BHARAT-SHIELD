"""
Agent 5 — Session State Store (SQLite)
Saves every simulation snapshot as a JSON blob to a local SQLite DB.
Enables State Hydration (browser refresh recovery) and War Games Archive (time-travel replay).
Zero new dependencies — uses Python built-in sqlite3.
"""
import sqlite3
import json
import datetime
import uuid
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bharat_shield_sessions.db")


def init_db():
    """Create sessions table if it doesn't exist. Called on FastAPI startup."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id  TEXT PRIMARY KEY,
                label        TEXT NOT NULL,
                region       TEXT,
                commodity    TEXT,
                scri_score   REAL,
                scri_band    TEXT,
                sim_data     TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Session store initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Session store init error: {e}")


def save_snapshot(sim_data: Dict[str, Any]) -> Optional[str]:
    """
    Serialize and persist a simulation result to the DB.
    Returns the snapshot_id on success, None on failure.
    """
    try:
        snapshot_id = str(uuid.uuid4())[:8]
        created_at  = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Build a human-readable label
        region    = sim_data.get("region", "Unknown Region")
        commodity = sim_data.get("commodity", "crude").upper()
        c_deficit = sim_data.get("crude", {}).get("scenario_parsed", {}).get("deficit_mmt", 0)
        g_deficit = sim_data.get("gas",   {}).get("scenario_parsed", {}).get("deficit_mmscmd", 0)
        scri      = sim_data.get("supply_risk_index", {})
        scri_score = scri.get("score", 0)
        scri_band  = scri.get("band", "")

        parts = []
        if c_deficit: parts.append(f"{c_deficit} MMT Crude")
        if g_deficit: parts.append(f"{g_deficit} MMSCMD Gas")
        deficit_str = " + ".join(parts) or "Simulation"
        label = f"{region} — {deficit_str}"

        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO snapshots
               (snapshot_id, label, region, commodity, scri_score, scri_band, sim_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (snapshot_id, label, region, commodity, scri_score, scri_band,
             json.dumps(sim_data), created_at)
        )
        conn.commit()
        conn.close()
        logger.info(f"Snapshot saved: {snapshot_id} — {label}")
        return snapshot_id

    except Exception as e:
        logger.error(f"Snapshot save error: {e}")
        return None


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """Return the most recent snapshot as a dict, or None."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT sim_data FROM snapshots ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"get_latest_snapshot error: {e}")
        return None


def list_snapshots(limit: int = 10) -> List[Dict[str, Any]]:
    """Return the last N snapshots as lightweight summary rows (no full sim_data)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            """SELECT snapshot_id, label, region, commodity, scri_score, scri_band, created_at
               FROM snapshots ORDER BY created_at DESC LIMIT ?""",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "snapshot_id": r[0],
                "label":       r[1],
                "region":      r[2],
                "commodity":   r[3],
                "scri_score":  r[4],
                "scri_band":   r[5],
                "created_at":  r[6],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"list_snapshots error: {e}")
        return []


def get_snapshot_by_id(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Return a specific snapshot's full sim_data by its ID (time-travel replay)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            "SELECT sim_data FROM snapshots WHERE snapshot_id = ?",
            (snapshot_id,)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"get_snapshot_by_id error: {e}")
        return None


def get_age_of_latest_seconds() -> Optional[float]:
    """Returns how many seconds ago the latest snapshot was created. None if no snapshots."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT created_at FROM snapshots ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            created = datetime.datetime.fromisoformat(row[0])
            if created.tzinfo is None:
                created = created.replace(tzinfo=datetime.timezone.utc)
            delta = datetime.datetime.now(datetime.timezone.utc) - created
            return delta.total_seconds()
        return None
    except Exception as e:
        logger.error(f"get_age_of_latest_seconds error: {e}")
        return None
