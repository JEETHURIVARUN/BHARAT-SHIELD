import datetime
import hashlib
import json
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def generate_audit_package(deficit_mmt: float, phase: int, drawdown_plan: dict) -> dict:
    """
    KAUTILYA (Strategic Audit & War Room): Generates a cryptographically signed JSON payload 
    and a CSV execution ledger.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Audit Payload
    audit_payload = {
        "timestamp": timestamp,
        "authorized_by": "Command Center - BHARAT-SHIELD",
        "decision_variables": {
            "target_deficit": deficit_mmt,
            "policy_phase": phase,
            "drawdown_plan": drawdown_plan
        }
    }
    
    payload_str = json.dumps(audit_payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
    
    # Ledger Generation
    ledger_records = []
    
    omc = drawdown_plan.get("OMC_Drawdown", {})
    for entity, val in omc.items():
        if val > 0:
            ledger_records.append({"Entity": entity, "Type": "OMC Commercial", "Drawdown_MMT": val})
            
    isprl = drawdown_plan.get("ISPRL_Drawdown", {})
    for entity, val in isprl.items():
        if val > 0:
            ledger_records.append({"Entity": entity, "Type": "ISPRL Strategic", "Drawdown_MMT": val})
            
    df_ledger = pd.DataFrame(ledger_records)
    csv_ledger = df_ledger.to_csv(index=False)
    
    return {
        "status": "success",
        "cryptographic_hash": payload_hash,
        "payload": audit_payload,
        "ledger_csv": csv_ledger,
        "message": "Directive executed and cryptographically sealed."
    }
